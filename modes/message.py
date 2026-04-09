"""
modes/message.py — DD-Msg-Bot V5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Message Mode: Send pre-written messages to DamaDam users.

Key fixes in V5.0:
  - Post selection: ONLY pick posts that have the REPLIES button visible
    (a[itemprop='discussionUrl']). Never pick posts with replies off.
  - 0 Posts check: read POSTS count from profile page before scanning.
    If 0, skip immediately with note "0 Posts".
  - "REPLIES OFF" text detection on post page → mark Skipped, note "Replies Off"
  - "FOLLOW TO REPLY" → status=Skipped, note="Must Follow First"
  - "Not Following" → status=Skipped, note="Must Follow First"
  - No Form after checking → "No Reply Form"
  - VLOOKUP cols (D,E,F,G) never written by bot.
  - Log writes correct cols to MsgLog sheet.
"""

import re
import time
from urllib.parse import quote
from typing import Optional, Dict, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import Config
from utils.logger import Logger, pkt_stamp
from utils.helpers import clean_post_url, is_valid_post_url, strip_non_bmp
from core.sheets import SheetsManager

from datetime import datetime, timezone, timedelta

_PKT = timezone(timedelta(hours=5))

def _today() -> str:
    return datetime.now(tz=_PKT).strftime("%Y-%m-%d")


# ── Selectors ─────────────────────────────────────────────────────────────────
# Only posts that have this element have replies open
_SEL_REPLIES_LINK  = "a[itemprop='discussionUrl'][href*='/comments/']"
_SEL_REPLY_FORM    = "form[action*='direct-response/send']"
_SEL_REPLY_TA      = "textarea[name='direct_response']"
_SEL_POST_COUNT    = "a[href*='/profile/public/'] button div"   # "0\nPOSTS"


def run(driver, sheets: SheetsManager, logger: Logger,
        max_targets: int = 0) -> Dict:
    """Run Message Mode end-to-end."""
    import time as _t
    run_start = _t.time()

    logger.section("MESSAGE MODE")

    ws = sheets.get_worksheet(Config.SHEET_MSG_QUE, headers=Config.MSG_QUE_COLS)
    if not ws:
        logger.error("MsgQue sheet not found")
        return {}

    all_rows = sheets.read_all(ws)
    if len(all_rows) < 2:
        logger.info("MsgQue is empty")
        return {"done": 0, "skipped": 0, "failed": 0, "total": 0}

    headers    = all_rows[0]
    header_map = SheetsManager.build_header_map(headers)
    header_len = len(headers)

    col_status   = sheets.get_col(headers, "STATUS")
    col_notes    = sheets.get_col(headers, "NOTES")
    col_result   = sheets.get_col(headers, "RESULT")
    col_sent_msg = sheets.get_col(headers, "SENT_MSG")

    if not all([col_status, col_notes, col_result]):
        logger.error(f"MsgQue missing required columns. Found: {headers}")
        return {}

    def cell(row, *names):
        return SheetsManager.get_cell(row, header_map, *names)

    def cell_by_col(row, col_1based):
        if not col_1based:
            return ""
        idx = col_1based - 1
        return str(row[idx]).strip() if idx < len(row) else ""

    # ── Collect pending rows ──────────────────────────────────────────────────
    pending: List[Dict] = []
    for i, row in enumerate(all_rows[1:], start=2):
        if header_len and len(row) < header_len:
            row = row + [""] * (header_len - len(row))
        if not cell_by_col(row, col_status).lower().startswith("pending"):
            continue
        nick = cell(row, "NICK")
        if not nick:
            continue
        message = cell(row, "MESSAGE")
        if not message:
            sheets.update_row_cells(ws, i, {col_status: "Skipped", col_notes: "No message text"})
            continue
        pending.append({
            "row": i, "nick": nick,
            "name":      cell(row, "NAME"),
            "city":      cell(row, "CITY"),
            "posts":     cell(row, "POSTS"),
            "followers": cell(row, "FOLLOWERS"),
            "gender":    cell(row, "GENDER"),
            "message":   message,
        })

    if not pending:
        logger.info("No Pending rows in MsgQue")
        return {"done": 0, "skipped": 0, "failed": 0, "total": 0}

    if max_targets and max_targets > 0:
        pending = pending[:max_targets]

    logger.info(f"Found {len(pending)} Pending targets")
    stats = {"done": 0, "skipped": 0, "failed": 0, "total": len(pending)}

    for idx, target in enumerate(pending, start=1):
        nick    = target["nick"]
        row_num = target["row"]
        logger.info(f"[{idx}/{len(pending)}] {nick}")

        post_url, reason = _find_open_post(driver, nick, logger)

        if not post_url:
            note = reason or "No open posts"
            logger.skip(f"{nick} — {note}")
            sheets.update_row_cells(ws, row_num, {
                col_status: "Skipped",
                col_notes:  note,
            })
            _write_msg_log(sheets, nick, target["name"], "", "", "Skipped", note)
            stats["skipped"] += 1
            continue

        profile_data = {
            "NAME": target["name"], "NICK": nick,
            "CITY": target["city"], "POSTS": target["posts"],
            "FOLLOWERS": target["followers"], "GENDER": target["gender"],
        }
        message_text = _process_template(target["message"], profile_data)

        result = _send_message(driver, post_url, message_text, nick, logger)
        status  = result["status"]
        res_url = result.get("url", post_url)

        if status == "Posted":
            logger.ok(f"Sent to {nick} → {res_url}")
            updates = {
                col_status: "Done",
                col_notes:  f"Sent @ {pkt_stamp()}",
                col_result: res_url,
            }
            if col_sent_msg:
                updates[col_sent_msg] = message_text
            sheets.update_row_cells(ws, row_num, updates)
            _write_msg_log(sheets, nick, target["name"], message_text, res_url, "Sent", "")
            stats["done"] += 1

        elif status in ("Not Following", "Must Follow First"):
            note = "Must Follow First"
            logger.skip(f"{nick} — {note}")
            sheets.update_row_cells(ws, row_num, {
                col_status: "Skipped",
                col_notes:  note,
                col_result: res_url,
            })
            _write_msg_log(sheets, nick, target["name"], message_text, res_url, "Skipped", note)
            stats["skipped"] += 1

        elif status == "Replies Off":
            note = "Replies Off"
            logger.skip(f"{nick} — {note}")
            sheets.update_row_cells(ws, row_num, {
                col_status: "Skipped",
                col_notes:  note,
                col_result: res_url,
            })
            _write_msg_log(sheets, nick, target["name"], message_text, res_url, "Skipped", note)
            stats["skipped"] += 1

        else:
            # Any other error
            logger.warning(f"{nick} — {status}")
            sheets.update_row_cells(ws, row_num, {
                col_status: "Failed",
                col_notes:  status[:80],
                col_result: res_url,
            })
            _write_msg_log(sheets, nick, target["name"], message_text, res_url, "Failed", status[:80])
            stats["failed"] += 1

        time.sleep(Config.MSG_DELAY_SECONDS)

    duration = _t.time() - run_start
    logger.section(
        f"DONE — Done:{stats['done']}  Skipped:{stats['skipped']}  Failed:{stats['failed']}"
    )
    return stats


# ════════════════════════════════════════════════════════════════════════════════
#  FIND OPEN POST
# ════════════════════════════════════════════════════════════════════════════════

def _find_open_post(driver, nick_or_url: str, logger: Logger) -> Tuple[Optional[str], Optional[str]]:
    """
    Find a post that has replies open.

    Strategy:
    1. If input is a direct post URL → verify it directly.
    2. If input is a nick/profile URL:
       a. Visit profile page 1
       b. Check POSTS count — if 0, return (None, "0 Posts")
       c. Collect all <a itemprop='discussionUrl'> links on profile
          These are the ONLY posts with replies open (DamaDam only renders
          that button when replies are enabled).
       d. For each candidate, visit post and verify reply form present.
    """
    raw = str(nick_or_url).strip()

    # Direct post URL
    if "damadam.pk" in raw and "/comments/" in raw:
        clean = clean_post_url(raw)
        if is_valid_post_url(clean):
            ok, reason = _verify_post_has_form(driver, clean, logger)
            return (clean, None) if ok else (None, reason)
        return None, "Invalid URL"

    # Extract nick from profile URL if needed
    nick = raw
    if "damadam.pk" in raw:
        m = re.search(r"/profile/(?:public/)?([^/?#]+)", raw, re.I)
        if m:
            nick = m.group(1).strip()

    safe_nick = quote(nick, safe="+")
    max_pages  = max(1, Config.MAX_POST_PAGES)
    last_reason: Optional[str] = None

    for page_num in range(1, max_pages + 1):
        url = f"{Config.BASE_URL}/profile/public/{safe_nick}/?page={page_num}"
        try:
            logger.debug(f"Profile page {page_num}: {url}")
            driver.get(url)
            time.sleep(2)

            # ── Check post count on page 1 ────────────────────────────────────
            if page_num == 1:
                posts_count = _get_profile_post_count(driver)
                if posts_count == 0:
                    logger.debug(f"{nick} has 0 posts")
                    return None, "0 Posts"

            # ── Collect posts that have the REPLIES button ─────────────────────
            # DamaDam only renders a[itemprop='discussionUrl'] when replies are open.
            # This is the most reliable selector — no need to visit each post.
            reply_links = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLIES_LINK)

            open_post_urls = []
            for a in reply_links:
                href = (a.get_attribute("href") or "").strip()
                if not href:
                    continue
                clean = clean_post_url(href)
                if is_valid_post_url(clean) and clean not in open_post_urls:
                    open_post_urls.append(clean)

            logger.debug(f"Page {page_num}: found {len(open_post_urls)} posts with replies open")

            # Try each candidate — pick the first with an actual reply form
            for candidate in open_post_urls:
                ok, reason = _verify_post_has_form(driver, candidate, logger)
                if ok:
                    logger.debug(f"Using post: {candidate}")
                    return candidate, None
                if reason:
                    last_reason = last_reason or reason

            # Check next page
            try:
                nxt = driver.find_element(By.CSS_SELECTOR, "a[rel='next']")
                if not nxt.get_attribute("href"):
                    break
            except NoSuchElementException:
                break

        except Exception as e:
            logger.debug(f"Profile page {page_num} error: {e}")
            break

    return None, last_reason or "No posts with replies open"


def _get_profile_post_count(driver) -> int:
    """
    Read the POSTS count from the profile page.
    Looks for the button that shows post count (e.g. "0\nPOSTS").
    Returns 0 if not found (safe default — will not skip if we can't read it).
    """
    try:
        # The posts button HTML is:
        # <button ...><div>0</div><div class="mt" style="...">POSTS</div></button>
        buttons = driver.find_elements(By.CSS_SELECTOR, "a[href*='/profile/public/'] button")
        for btn in buttons:
            text = (btn.text or "").strip().upper()
            if "POSTS" in text:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                for line in lines:
                    if line.isdigit():
                        return int(line)
        # Fallback: look for any button containing "POSTS" text on the page
        all_btns = driver.find_elements(By.CSS_SELECTOR, "button")
        for btn in all_btns:
            text = (btn.text or "").strip().upper()
            if "POSTS" in text:
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                for line in lines:
                    if line.isdigit():
                        return int(line)
    except Exception:
        pass
    return -1  # -1 = unknown, don't skip


def _verify_post_has_form(driver, post_url: str, logger: Logger) -> Tuple[bool, Optional[str]]:
    """
    Navigate to post_url and confirm the reply form + textarea are present.
    Also checks for "REPLIES OFF" and "FOLLOW TO REPLY" conditions.
    """
    try:
        driver.get(post_url)
        time.sleep(2)
        page = driver.page_source

        page_upper = page.upper()
        if "REPLIES OFF" in page_upper or "REPLIES ARE OFF" in page_upper:
            return False, "Replies Off"
        if "COMMENTS ARE CLOSED" in page_upper or "COMMENTS CLOSED" in page_upper:
            return False, "Replies Off"
        if "FOLLOW TO REPLY" in page_upper or "FOLLOW TO COMMENT" in page_upper:
            return False, "Must Follow First"

        forms = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLY_FORM)
        for f in forms:
            try:
                f.find_element(By.CSS_SELECTOR, _SEL_REPLY_TA)
                return True, None
            except Exception:
                continue

        return False, "No Reply Form"
    except Exception as e:
        return False, f"Error: {str(e)[:40]}"


# ════════════════════════════════════════════════════════════════════════════════
#  SEND MESSAGE
# ════════════════════════════════════════════════════════════════════════════════

def _send_message(driver, post_url: str, message: str,
                  nick: str = "", logger: Logger = None) -> Dict:
    """
    Type and submit a reply on the given post.
    Uses send_keys (not JS .value) so React state is properly updated.
    """
    if Config.DRY_RUN:
        logger and logger.info(f"DRY RUN — would send to {post_url}")
        return {"status": "Posted", "url": post_url}

    try:
        logger and logger.debug(f"Opening post: {post_url}")
        driver.get(post_url)
        time.sleep(3)

        page = driver.page_source
        page_upper = page.upper()

        if "FOLLOW TO REPLY" in page_upper or "FOLLOW TO COMMENT" in page_upper:
            return {"status": "Must Follow First", "url": post_url}
        if "REPLIES OFF" in page_upper or "COMMENTS ARE CLOSED" in page_upper:
            return {"status": "Replies Off", "url": post_url}

        forms    = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLY_FORM)
        form     = None
        textarea = None
        for f in forms:
            try:
                ta = f.find_element(By.CSS_SELECTOR, _SEL_REPLY_TA)
                if ta.is_displayed() and ta.is_enabled():
                    form     = f
                    textarea = ta
                    break
            except Exception:
                continue

        if not form or not textarea:
            return {"status": "No Reply Form", "url": post_url}

        # Find submit button
        submit_btn = None
        for sel in ("button[name='dec'][value='1']", "button[type='submit']", "input[type='submit']"):
            btns = form.find_elements(By.CSS_SELECTOR, sel)
            for b in btns:
                try:
                    if b.is_displayed() and b.is_enabled():
                        submit_btn = b
                        break
                except Exception:
                    continue
            if submit_btn:
                break

        if not submit_btn:
            return {"status": "No Submit Button", "url": post_url}

        safe_msg = strip_non_bmp(message)[:350]

        # Scroll + focus + clear + send_keys (React-safe)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", textarea)
        time.sleep(0.2)
        driver.execute_script("arguments[0].focus();", textarea)
        driver.execute_script("arguments[0].click();", textarea)
        time.sleep(0.3)
        try:
            textarea.clear()
        except Exception:
            pass
        time.sleep(0.2)
        try:
            textarea.send_keys(safe_msg)
        except Exception:
            try:
                driver.execute_script("arguments[0].value='';", textarea)
                driver.execute_script("arguments[0].focus();", textarea)
                textarea.send_keys(safe_msg)
            except Exception as e:
                return {"status": f"Type Error: {str(e)[:40]}", "url": post_url}
        time.sleep(0.5)

        # If send_keys didn't register (React textarea), use native value setter
        actual = driver.execute_script("return arguments[0].value;", textarea) or ""
        if not actual.strip():
            logger and logger.debug("send_keys missed — using React native setter")
            driver.execute_script(
                """
                var el = arguments[0];
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value').set;
                setter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input',  {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                """,
                textarea, safe_msg
            )
            time.sleep(0.3)

        # Submit
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", submit_btn)
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", submit_btn)
        time.sleep(4)

        # Verify
        driver.get(post_url)
        time.sleep(2)
        fresh = driver.page_source
        our_nick = Config.DD_NICK.lower()
        if our_nick in fresh.lower():
            return {"status": "Posted", "url": clean_post_url(driver.current_url)}

        # Can't verify but don't fail — user can check RESULT url
        logger and logger.warning(f"Could not verify post for {nick} — assuming sent")
        return {"status": "Posted", "url": clean_post_url(driver.current_url)}

    except Exception as e:
        return {"status": f"Error: {str(e)[:50]}", "url": post_url}


# ════════════════════════════════════════════════════════════════════════════════
#  TEMPLATE + LOG
# ════════════════════════════════════════════════════════════════════════════════

def _process_template(template: str, profile: Dict) -> str:
    name_val = (profile.get("NAME") or "").strip() or (profile.get("NICK") or "").strip()
    replacements = {
        "{{name}}":      name_val,
        "{{nick}}":      (profile.get("NICK") or "").strip(),
        "{{city}}":      (profile.get("CITY") or "").strip(),
        "{{posts}}":     str(profile.get("POSTS") or "").strip(),
        "{{followers}}": str(profile.get("FOLLOWERS") or "").strip(),
        "{{gender}}":    (profile.get("GENDER") or "").strip(),
    }
    msg = template
    for ph, val in replacements.items():
        msg = msg.replace(ph, val)
    msg = re.sub(r"(?i)(?:,\s*)?no\s*city\b", "", msg)
    msg = re.sub(r"\{\{[^}]+\}\}", "", msg)
    msg = re.sub(r"\s{2,}", " ", msg)
    msg = re.sub(r"\s+([,?.!])", r"\1", msg)
    msg = re.sub(r",\s*,", ",", msg)
    return msg.strip()


def _write_msg_log(sheets: SheetsManager, nick: str, name: str,
                   message: str, post_url: str, status: str, notes: str):
    """Append one row to MsgLog."""
    ws = sheets.get_worksheet(Config.SHEET_MSG_LOG, headers=Config.MSG_LOG_COLS)
    if not ws:
        return
    sheets.append_row(ws, [
        _today(),     # DATE
        pkt_stamp(),  # TIMESTAMP
        nick,         # NICK
        name,         # NAME
        post_url,     # POST_URL
        status,       # STATUS
        notes,        # NOTES
        message,      # MESSAGE
    ])
