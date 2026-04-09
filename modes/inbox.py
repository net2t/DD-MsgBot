"""
modes/inbox.py — DD-Msg-Bot V5.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inbox Mode: Sync DamaDam inbox + activity feed.

Sheet structure:
  Inbox    — one row per unique NICK, upserted on each sync
  InboxLog — append-only history of all events

Flow:
  Phase 1 — Fetch /inbox/ conversations
             Parse NICK, TID, TYPE, last message, conv_url
             Upsert into Inbox (one row per NICK — no duplicates)
             Append to InboxLog (de-dup by nick+last_msg content)

  Phase 2 — Fetch /inbox/activity/ with pagination
             Parse structured data: MODE, NICK, POST text, action, time
             Append to InboxLog (de-dup by nick+message content)
             Stops when no NEXT page link found

  Phase 3 — Send pending replies
             Inbox rows where MY_REPLY filled AND STATUS=Pending
             Uses /inbox/ page to find the reply form by TID
             Submits via form action /direct-response/send/

Reply HTML structure (from /inbox/ page):
  <form action="/1-on-1/from-single-notif/">
    <button name="tid" value="2464609">...1 ON 1 with Nick...</button>
  </form>
  <form action="/direct-response/send/">
    <input name="tuid"  value="2464609">
    <input name="obid"  value="169">
    <input name="obtp"  value="7">
    <input name="poid"  value="656257">
    <input name="origin" value="24">
    <input name="drl"   value="1">
    <textarea name="direct_response">
    <button name="dec" value="1">SEND</button>
  </form>

Activity HTML structure (one block):
  <div class="mbl mtl">
    <div style="background:#f9f9f9">
      <a href="/comments/text/41902128/35/">
        <button ...>
          <span class="ct">POST</span>  ← MODE
          <span class="ct">►</span>
          <span class="ct"><b><bdi>GangSter.GurlYa</bdi>:</b> post text...</span>  ← NICK + POST
        </button>
      </a>
    </div>
    <div style="background:white">
      <div ...>You replied to <b>GangSter.GurlYa</b> on this post</div>  ← ACTION
      <div ...><span>REMOVE</span><span>last reply - 1 hour ago</span></div>  ← TID in form
      <form action="/inbox/activity/remove/">
        <button name="pl" value="3:41902128:3349687">  ← TID is last part
    </div>
  </div>
"""

import re
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone, timedelta

from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException

from config import Config
from utils.logger import Logger, pkt_stamp
from utils.helpers import strip_non_bmp
from core.sheets import SheetsManager

_PKT = timezone(timedelta(hours=5))

def _today() -> str:
    return datetime.now(tz=_PKT).strftime("%Y-%m-%d")


# ── URLs ──────────────────────────────────────────────────────────────────────
_URL_INBOX    = f"{Config.BASE_URL}/inbox/"
_URL_ACTIVITY = f"{Config.BASE_URL}/inbox/activity/"

# ── Inbox selectors ───────────────────────────────────────────────────────────
_SEL_BLOCK        = "div.mbl.mtl"
_SEL_TID_BTN      = "button[name='tid']"          # TID in inbox
_SEL_NICK_BDI     = "div.cl.lsp.nos b bdi"        # Nick text
_SEL_MSG_SPAN     = "div.cl.lsp.nos span bdi"     # Last message
_SEL_TIME_SPAN    = "span[style*='color:#999']"    # Relative time
_SEL_TYPE_SPAN    = "div.sp.cs.mrs span"           # Type (1ON1/POST)

# ── Reply form selectors ──────────────────────────────────────────────────────
_SEL_REPLY_FORM   = "form[action*='/direct-response/send']"
_SEL_REPLY_TA     = "textarea[name='direct_response']"
_SEL_SEND_BTN     = "button[name='dec'][value='1']"

# ── Activity selectors ────────────────────────────────────────────────────────
_SEL_ACT_MODE     = "div.sp.cs.mrs span.ct"       # POST / 1ON1 / MEHFIL
_SEL_ACT_CONTENT  = "div.sp.cm.nos span.ct"       # Nick + post text
_SEL_ACT_ACTION   = "div.sp.lsp.nos"              # "You replied to Nick on this post"
_SEL_ACT_REMOVE   = "form[action*='/inbox/activity/remove/'] button[name='pl']"  # value has TID
_SEL_ACT_LINK     = "a[href*='/comments/']"        # Post URL
_SEL_NEXT_PAGE    = "a[href*='?page=']"            # Pagination


def run(driver, sheets: SheetsManager, logger: Logger) -> Dict:
    """Run Inbox Mode: sync + activity + send replies."""
    import time as _t
    run_start = _t.time()
    logger.section("INBOX MODE")

    ws_inbox = sheets.get_worksheet(Config.SHEET_INBOX,     headers=Config.INBOX_COLS)
    ws_log   = sheets.get_worksheet(Config.SHEET_INBOX_LOG, headers=Config.INBOX_LOG_COLS)
    if not ws_inbox or not ws_log:
        logger.error("Inbox or InboxLog sheet not found — run Setup first")
        return {}

    # ── Load existing Inbox → nick→row map ────────────────────────────────────
    all_inbox  = sheets.read_all(ws_inbox)
    inbox_hdrs = all_inbox[0] if all_inbox else Config.INBOX_COLS
    inbox_hmap = SheetsManager.build_header_map(inbox_hdrs)

    nick_to_row: Dict[str, int] = {}
    for i, row in enumerate(all_inbox[1:], start=2):
        n = SheetsManager.get_cell(row, inbox_hmap, "NICK").strip().lower()
        if n:
            nick_to_row[n] = i

    # ── Load InboxLog → build today's de-dup set (by nick+message content) ───
    all_log  = sheets.read_all(ws_log)
    log_hdrs = all_log[0] if all_log else Config.INBOX_LOG_COLS
    log_hmap = SheetsManager.build_header_map(log_hdrs)

    today = _today()
    # Key: nick|direction|message_content[:80]
    logged_today: set = set()
    for row in all_log[1:]:
        d = SheetsManager.get_cell(row, log_hmap, "DATE")
        if d != today:
            continue
        n = SheetsManager.get_cell(row, log_hmap, "NICK").lower()
        dr = SheetsManager.get_cell(row, log_hmap, "DIRECTION").upper()
        m = SheetsManager.get_cell(row, log_hmap, "MESSAGE")[:80]
        logged_today.add(f"{n}|{dr}|{m}")

    # ── Column numbers for Inbox sheet ────────────────────────────────────────
    col_nick     = sheets.get_col(inbox_hdrs, "NICK")
    col_tid      = sheets.get_col(inbox_hdrs, "TID")
    col_type     = sheets.get_col(inbox_hdrs, "TYPE")
    col_last_msg = sheets.get_col(inbox_hdrs, "LAST_MSG")
    col_date     = sheets.get_col(inbox_hdrs, "DATE")
    col_time_str = sheets.get_col(inbox_hdrs, "TIME_STR")
    col_my_reply = sheets.get_col(inbox_hdrs, "MY_REPLY")
    col_status   = sheets.get_col(inbox_hdrs, "STATUS")
    col_conv_url = sheets.get_col(inbox_hdrs, "CONV_URL")
    col_updated  = sheets.get_col(inbox_hdrs, "UPDATED")
    col_notes    = sheets.get_col(inbox_hdrs, "NOTES")

    # ══════════════════════════════════════════════════════════════════════════
    #  Phase 1: Fetch inbox
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("Phase 1: Fetching inbox...")
    inbox_items = _fetch_inbox(driver, logger)
    logger.info(f"  {len(inbox_items)} conversations found")

    new_count     = 0
    updated_count = 0

    for item in inbox_items:
        nick     = item.get("nick", "").strip()
        tid      = item.get("tid", "").strip()
        itype    = item.get("type", "")
        last_msg = item.get("last_msg", "")
        time_str = item.get("time_str", "")
        conv_url = item.get("conv_url", "")

        if not nick:
            continue

        # InboxLog de-dup by content (not just nick)
        log_key = f"{nick.lower()}|IN|{last_msg[:80]}"
        if log_key not in logged_today:
            _append_log(sheets, ws_log, today, pkt_stamp(),
                        nick, tid, itype, "IN", last_msg, conv_url, "Received")
            logged_today.add(log_key)

        # Upsert Inbox sheet — one row per NICK
        if nick.lower() in nick_to_row:
            row_n = nick_to_row[nick.lower()]
            # Get current status to decide whether to reset
            cur_row = all_inbox[row_n - 1] if row_n - 1 < len(all_inbox) else []
            cur_status = SheetsManager.get_cell(cur_row, inbox_hmap, "STATUS").lower()
            updates = {}
            if col_tid:      updates[col_tid]      = tid
            if col_type:     updates[col_type]      = itype
            if col_last_msg: updates[col_last_msg]  = last_msg
            if col_date:     updates[col_date]      = today
            if col_time_str: updates[col_time_str]  = time_str
            if col_conv_url: updates[col_conv_url]  = conv_url
            if col_updated:  updates[col_updated]   = pkt_stamp()
            # Reset to New only if previous was Done/empty (new message arrived)
            if cur_status in ("done", "") and col_status:
                updates[col_status] = "New"
            sheets.update_row_cells(ws_inbox, row_n, updates)
            updated_count += 1
        else:
            row_vals = [""] * len(inbox_hdrs)
            def _s(col, val):
                if col: row_vals[col - 1] = val
            _s(col_nick,     nick)
            _s(col_tid,      tid)
            _s(col_type,     itype)
            _s(col_last_msg, last_msg)
            _s(col_date,     today)
            _s(col_time_str, time_str)
            _s(col_my_reply, "")
            _s(col_status,   "New")
            _s(col_conv_url, conv_url)
            _s(col_updated,  pkt_stamp())
            _s(col_notes,    "")
            sheets.append_row(ws_inbox, row_vals)
            nick_to_row[nick.lower()] = len(all_inbox) + new_count + 1
            new_count += 1
            logger.ok(f"  New: [{itype}] {nick}")

    # ══════════════════════════════════════════════════════════════════════════
    #  Phase 2: Fetch activity (paginated)
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("Phase 2: Fetching activity...")
    activities = _fetch_activity(driver, logger)
    logger.info(f"  {len(activities)} activity items found")

    act_logged = 0
    for act in activities:
        nick = act.get("nick", "").strip()
        msg  = act.get("text", "")
        url  = act.get("url", "")
        tid  = act.get("tid", "")
        atype = act.get("type", "ACTIVITY")
        time_s = act.get("time_str", "")

        log_key = f"{nick.lower()}|ACTIVITY|{msg[:80]}"
        if log_key in logged_today:
            logger.debug(f"  Dup skip: {nick} — {msg[:40]}")
            continue

        _append_log(sheets, ws_log, today, pkt_stamp(),
                    nick, tid, atype, "ACTIVITY", msg, url, "Logged")
        logged_today.add(log_key)
        act_logged += 1

    logger.info(f"  {act_logged} new activity items logged")

    # ══════════════════════════════════════════════════════════════════════════
    #  Phase 3: Send pending replies
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("Phase 3: Sending pending replies...")

    # Re-read Inbox (may have new rows)
    all_inbox  = sheets.read_all(ws_inbox)
    inbox_hdrs = all_inbox[0] if all_inbox else Config.INBOX_COLS
    inbox_hmap = SheetsManager.build_header_map(inbox_hdrs)

    col_status   = sheets.get_col(inbox_hdrs, "STATUS")
    col_notes    = sheets.get_col(inbox_hdrs, "NOTES")
    col_updated  = sheets.get_col(inbox_hdrs, "UPDATED")

    def gcell(row, *names):
        return SheetsManager.get_cell(row, inbox_hmap, *names)

    pending_replies = []
    for i, row in enumerate(all_inbox[1:], start=2):
        reply  = gcell(row, "MY_REPLY").strip()
        status = gcell(row, "STATUS").lower()
        if reply and status == "pending":
            pending_replies.append({
                "row":      i,
                "nick":     gcell(row, "NICK"),
                "tid":      gcell(row, "TID"),
                "type":     gcell(row, "TYPE"),
                "reply":    reply,
                "conv_url": gcell(row, "CONV_URL"),
            })

    logger.info(f"  {len(pending_replies)} pending replies to send")

    # Build TID → conv_url from current inbox
    tid_to_url = {it["tid"]: it["conv_url"] for it in inbox_items if it.get("tid")}

    sent_cnt   = 0
    failed_cnt = 0

    for idx, item in enumerate(pending_replies, start=1):
        nick     = item["nick"]
        tid      = item["tid"]
        reply    = item["reply"]
        row_n    = item["row"]
        conv_url = tid_to_url.get(tid, "").strip() or item.get("conv_url", "") or _URL_INBOX

        logger.info(f"  [{idx}/{len(pending_replies)}] → {nick} (tid={tid})")
        ok, sent_url = _send_reply_by_tid(driver, tid, reply, nick, logger)

        if ok:
            logger.ok(f"    Reply sent → {nick}")
            sheets.update_row_cells(ws_inbox, row_n, {
                col_status:  "Done",
                col_notes:   f"Replied @ {pkt_stamp()}",
                col_updated: pkt_stamp(),
            })
            _append_log(sheets, ws_log, today, pkt_stamp(),
                        nick, tid, item["type"], "OUT",
                        reply, sent_url or conv_url, "Sent")
            sent_cnt += 1
        else:
            logger.warning(f"    Reply failed → {nick}")
            sheets.update_row_cells(ws_inbox, row_n, {
                col_status:  "Failed",
                col_notes:   f"Send failed @ {pkt_stamp()}",
                col_updated: pkt_stamp(),
            })
            _append_log(sheets, ws_log, today, pkt_stamp(),
                        nick, tid, item["type"], "OUT",
                        reply, conv_url, "Failed")
            failed_cnt += 1

        time.sleep(2)

    duration = _t.time() - run_start
    logger.section(
        f"INBOX DONE — New:{new_count} Updated:{updated_count} "
        f"Activity:{act_logged} Replies Sent:{sent_cnt} Failed:{failed_cnt} "
        f"({duration:.0f}s)"
    )
    return {
        "new": new_count, "updated": updated_count,
        "activity": act_logged, "sent": sent_cnt, "failed": failed_cnt,
    }


# ════════════════════════════════════════════════════════════════════════════════
#  FETCH INBOX
# ════════════════════════════════════════════════════════════════════════════════

def _fetch_inbox(driver, logger: Logger) -> List[Dict]:
    """Open /inbox/ and parse all conversation blocks."""
    try:
        driver.get(_URL_INBOX)
        time.sleep(3)

        items: List[Dict] = []
        seen_tids:  set = set()
        seen_nicks: set = set()

        blocks = driver.find_elements(By.CSS_SELECTOR, _SEL_BLOCK)
        if not blocks:
            logger.warning("  No inbox blocks found (empty or session expired)")
            return []

        for block in blocks[:60]:
            try:
                item = _parse_inbox_block(block)
                if not item:
                    continue
                tid  = item.get("tid", "")
                nick = item.get("nick", "").lower()
                if not nick:
                    continue
                if tid and tid in seen_tids:
                    continue
                if not tid and nick in seen_nicks:
                    continue
                if tid:
                    seen_tids.add(tid)
                seen_nicks.add(nick)
                items.append(item)
            except Exception as e:
                logger.debug(f"  Block parse error: {e}")

        return items
    except Exception as e:
        logger.error(f"Inbox fetch error: {e}")
        return []


def _parse_inbox_block(block) -> Optional[Dict]:
    """Parse one inbox div.mbl.mtl block."""
    # TID from button[name='tid']
    tid = ""
    try:
        btns = block.find_elements(By.CSS_SELECTOR, _SEL_TID_BTN)
        if btns:
            tid = (btns[0].get_attribute("value") or "").strip()
    except Exception:
        pass

    # Type (1ON1 / POST / MEHFIL)
    conv_type = ""
    try:
        spans = block.find_elements(By.CSS_SELECTOR, _SEL_TYPE_SPAN)
        if spans:
            raw = (spans[0].text or "").strip().upper()
            if "1" in raw and "ON" in raw:
                conv_type = "1ON1"
            elif "POST" in raw:
                conv_type = "POST"
            elif "MEHFIL" in raw:
                conv_type = "MEHFIL"
            else:
                conv_type = raw[:15]
    except Exception:
        pass

    # Nick
    nick = ""
    try:
        els = block.find_elements(By.CSS_SELECTOR, _SEL_NICK_BDI)
        if els:
            nick = (els[0].text or "").strip()
    except Exception:
        pass
    if not nick:
        return None

    # Last message
    last_msg = ""
    try:
        els = block.find_elements(By.CSS_SELECTOR, _SEL_MSG_SPAN)
        if els:
            last_msg = (els[0].text or "").strip()
    except Exception:
        pass

    # Time
    time_str = ""
    try:
        els = block.find_elements(By.CSS_SELECTOR, _SEL_TIME_SPAN)
        if els:
            time_str = (els[0].text or "").strip()
    except Exception:
        pass

    # Conv URL — prefer comments link, fallback to inbox
    conv_url = _URL_INBOX
    try:
        links = block.find_elements(
            By.CSS_SELECTOR,
            "a[href*='/comments/'], a[href*='/content/']"
        )
        for a in links:
            href = (a.get_attribute("href") or "").strip()
            if href:
                conv_url = href if href.startswith("http") else f"{Config.BASE_URL}{href}"
                break
    except Exception:
        pass

    return {
        "tid":      tid,
        "nick":     nick,
        "type":     conv_type,
        "last_msg": last_msg,
        "time_str": time_str,
        "conv_url": conv_url,
    }


# ════════════════════════════════════════════════════════════════════════════════
#  FETCH ACTIVITY  (paginated)
# ════════════════════════════════════════════════════════════════════════════════

def _fetch_activity(driver, logger: Logger,
                    max_pages: int = 10, max_items: int = 200) -> List[Dict]:
    """
    Fetch /inbox/activity/ with pagination.
    Stops when no NEXT page link or max_pages reached.

    Each activity block structure:
      MODE: POST/1ON1/MEHFIL from span.ct
      NICK: from <bdi> inside span.ct content area
      POST: post text from same span.ct content
      ACTION: "You replied to Nick on this post" from div.sp.lsp.nos
      TID:   last number in button[name='pl'] value "3:41902128:3349687"
      TIME:  "last reply - 1 hour ago" from right-side span
      URL:   from <a href='/comments/...'>
    """
    items: List[Dict] = []
    seen_keys: set    = set()
    page_num  = 1

    while page_num <= max_pages and len(items) < max_items:
        url = f"{_URL_ACTIVITY}?page={page_num}"
        try:
            driver.get(url)
            time.sleep(2.5)

            blocks = driver.find_elements(By.CSS_SELECTOR, _SEL_BLOCK)
            if not blocks:
                logger.debug(f"  Activity page {page_num}: no blocks, stopping")
                break

            page_new = 0
            for block in blocks:
                try:
                    act = _parse_activity_block(block)
                    if not act:
                        continue

                    # De-dup key: nick + message content
                    key = f"{act['nick'].lower()}|{act['text'][:80]}"
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    items.append(act)
                    page_new += 1
                except Exception:
                    continue

            logger.debug(f"  Activity page {page_num}: {page_new} new items")

            # Check for NEXT page
            has_next = False
            try:
                next_links = driver.find_elements(By.CSS_SELECTOR, _SEL_NEXT_PAGE)
                for a in next_links:
                    href = (a.get_attribute("href") or "")
                    text = (a.text or "").strip().upper()
                    if f"page={page_num + 1}" in href or "NEXT" in text:
                        has_next = True
                        break
            except Exception:
                pass

            if not has_next:
                logger.debug(f"  Activity: no next page after page {page_num}, stopping")
                break

            page_num += 1

        except Exception as e:
            logger.error(f"Activity page {page_num} error: {e}")
            break

    return items


def _parse_activity_block(block) -> Optional[Dict]:
    """
    Parse one activity div.mbl.mtl block.

    Returns dict with:
      nick, tid, type, text, url, time_str, action
    """
    # ── Post link + URL ────────────────────────────────────────────────────────
    url = ""
    try:
        links = block.find_elements(By.CSS_SELECTOR, _SEL_ACT_LINK)
        if links:
            href = (links[0].get_attribute("href") or "").strip()
            if href:
                url = href if href.startswith("http") else f"{Config.BASE_URL}{href}"
    except Exception:
        pass

    # ── MODE (POST / 1ON1 / MEHFIL) ───────────────────────────────────────────
    mode = ""
    try:
        mode_els = block.find_elements(By.CSS_SELECTOR, _SEL_ACT_MODE)
        if mode_els:
            raw = (mode_els[0].text or "").strip().upper()
            if "1" in raw and "ON" in raw:
                mode = "1ON1"
            elif "POST" in raw:
                mode = "POST"
            elif "MEHFIL" in raw:
                mode = "MEHFIL"
            else:
                mode = raw[:10] or "ACTIVITY"
    except Exception:
        pass

    # ── NICK + POST text from content span ────────────────────────────────────
    nick     = ""
    post_text = ""
    try:
        content_els = block.find_elements(By.CSS_SELECTOR, _SEL_ACT_CONTENT)
        if content_els:
            # Full text: "GangSter.GurlYa: بهادر نياڻيون..."
            raw = (content_els[0].text or "").strip()
            # Try to get nick from <bdi> inside content
            bdi_els = content_els[0].find_elements(By.CSS_SELECTOR, "bdi")
            if bdi_els:
                nick = (bdi_els[0].text or "").strip().rstrip(":")
            # Extract post text (after "nick:")
            if ":" in raw and not nick:
                nick = raw.split(":")[0].strip()
                post_text = raw.split(":", 1)[1].strip() if ":" in raw else ""
            elif nick:
                post_text = raw[len(nick):].lstrip(":").strip()
    except Exception:
        pass

    # ── ACTION text (e.g. "You replied to GangSter.GurlYa on this post") ─────
    action = ""
    try:
        action_els = block.find_elements(By.CSS_SELECTOR, _SEL_ACT_ACTION)
        if action_els:
            action = (action_els[0].text or "").strip()
            # Extract nick from action if not already found
            if not nick:
                m = re.search(r"to\s+(\S+)\s+on", action, re.I)
                if m:
                    nick = m.group(1).strip()
    except Exception:
        pass

    # ── TID from remove button value "3:41902128:3349687" → last part ─────────
    tid = ""
    try:
        remove_btns = block.find_elements(By.CSS_SELECTOR, _SEL_ACT_REMOVE)
        if remove_btns:
            val = (remove_btns[0].get_attribute("value") or "").strip()
            # Format: "3:postid:tid"
            parts = val.split(":")
            if len(parts) >= 3:
                tid = parts[-1].strip()
    except Exception:
        pass

    # ── TIME ──────────────────────────────────────────────────────────────────
    time_str = ""
    try:
        # Look for "last reply - X ago" or similar time text
        all_spans = block.find_elements(By.CSS_SELECTOR, "span")
        for sp in all_spans:
            t = (sp.text or "").strip().lower()
            if "ago" in t or "min" in t or "hour" in t:
                time_str = t
                break
    except Exception:
        pass

    if not nick and not action:
        return None

    # Build full text for logging
    parts_text = []
    if mode:
        parts_text.append(mode)
    if nick:
        parts_text.append(nick)
    if post_text:
        parts_text.append(post_text[:100])
    if action:
        parts_text.append(action)
    if time_str:
        parts_text.append(time_str)
    text = " | ".join(p for p in parts_text if p)[:300]

    return {
        "nick":     nick,
        "tid":      tid,
        "type":     mode or "ACTIVITY",
        "text":     text,
        "url":      url,
        "time_str": time_str,
        "action":   action,
    }


# ════════════════════════════════════════════════════════════════════════════════
#  SEND REPLY  (TID-based — uses /inbox/ reply form)
# ════════════════════════════════════════════════════════════════════════════════

def _send_reply_by_tid(driver, tid: str, reply_text: str,
                        nick: str, logger: Logger) -> Tuple[bool, str]:
    """
    Send a reply using the inbox reply form.

    Strategy:
    1. Open /inbox/ page
    2. Find the reply form matching our TID (input[name='tuid'][value=TID])
    3. Fill textarea, click SEND (dec=1)

    The /inbox/ page shows all active conversations with reply forms.
    Each form has <input name='tuid' value='TID'>.
    This is the cleanest approach — no need to navigate to each post URL.
    """
    safe_reply = strip_non_bmp(reply_text)[:350]

    try:
        driver.get(_URL_INBOX)
        time.sleep(3)

        # Find the reply form for this specific TID
        target_form = None
        target_ta   = None

        if tid:
            # Look for form with matching tuid
            forms = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLY_FORM)
            for form in forms:
                try:
                    tuid_input = form.find_element(
                        By.CSS_SELECTOR, f"input[name='tuid'][value='{tid}']"
                    )
                    # Found the right form — check textarea
                    ta = form.find_element(By.CSS_SELECTOR, _SEL_REPLY_TA)
                    if ta.is_displayed() or True:  # May be hidden until clicked
                        target_form = form
                        target_ta   = ta
                        break
                except Exception:
                    continue

        # Fallback: use first available form
        if not target_form:
            forms = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLY_FORM)
            for form in forms:
                try:
                    ta = form.find_element(By.CSS_SELECTOR, _SEL_REPLY_TA)
                    target_form = form
                    target_ta   = ta
                    break
                except Exception:
                    continue

        if not target_form or not target_ta:
            logger.debug(f"  No reply form found for {nick} (tid={tid})")
            return False, ""

        # Find SEND button (dec=1, not BLOCK dec=0 or SKIP dec=3)
        send_btn = None
        try:
            send_btn = target_form.find_element(By.CSS_SELECTOR, _SEL_SEND_BTN)
        except Exception:
            try:
                send_btn = target_form.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except Exception:
                pass

        if not send_btn:
            logger.debug(f"  No SEND button for {nick}")
            return False, ""

        # Type the reply
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'}); arguments[0].focus();",
            target_ta
        )
        time.sleep(0.3)
        try:
            target_ta.clear()
        except Exception:
            pass
        time.sleep(0.2)
        target_ta.send_keys(safe_reply)
        time.sleep(0.5)

        # Verify text was entered
        actual = driver.execute_script("return arguments[0].value;", target_ta) or ""
        if not actual.strip():
            # React native setter fallback
            driver.execute_script(
                """
                var el = arguments[0];
                var setter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype, 'value').set;
                setter.call(el, arguments[1]);
                el.dispatchEvent(new Event('input',  {bubbles:true}));
                el.dispatchEvent(new Event('change', {bubbles:true}));
                """,
                target_ta, safe_reply
            )
            time.sleep(0.3)

        # Click SEND
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", send_btn
        )
        time.sleep(0.2)
        driver.execute_script("arguments[0].click();", send_btn)
        time.sleep(3)

        return True, driver.current_url

    except Exception as e:
        logger.debug(f"  Reply error for {nick}: {e}")
        return False, ""


# ════════════════════════════════════════════════════════════════════════════════
#  LOG HELPER
# ════════════════════════════════════════════════════════════════════════════════

def _append_log(sheets: SheetsManager, ws_log,
                date: str, timestamp: str,
                nick: str, tid: str, conv_type: str, direction: str,
                message: str, url: str, status: str):
    """Append one row to InboxLog."""
    sheets.append_row(ws_log, [
        date,       # DATE
        timestamp,  # TIMESTAMP
        nick,       # NICK
        tid,        # TID
        conv_type,  # TYPE
        direction,  # DIRECTION
        message,    # MESSAGE
        url,        # CONV_URL
        status,     # STATUS
    ])
