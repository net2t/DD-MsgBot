"""
modes/messages.py — DD-Msg-Bot V4.1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unified Message Mode: Combines inbox and activity into one comprehensive system
  Phase 1 — Fetch DamaDam inbox (/inbox/)
             Parse each conversation block → TID, NICK, TYPE, last message
             Sync new conversations into MessageQueue sheet
             Log all items to MessageLog with full detail
  Phase 2 — Fetch activity feed (/inbox/activity/)
             Log each activity item to MessageLog sheet
  Phase 3 — Send pending replies
             Rows in MessageQueue where MY_REPLY has text + STATUS=Pending
             Navigate to the conversation, extract hidden form fields,
             and submit via proper form POST (CSRF + tuid + obid + poid)

New Sheet Structure:
- MessageQueue: Replaces InboxQue, organized by person record ID
- MessageLog: Replaces InboxLog, organized by date with complete history
- Removed: RunLog, Logs (unnecessary)

DamaDam inbox / reply HTML structure:
  Each inbox item → div.mbl.mtl containing:
    button[name='tid'] value="<user_id>"          ← stable user ID
    div.cl.lsp.nos b bdi                          ← nickname
    span.mrs bdi                                  ← last message text
    span[style*='color:#999']                     ← relative time "1 hour ago"

  Reply form on conversation/post pages:
    <form action="/direct-response/send/" method="POST">
      <input name="csrfmiddlewaretoken" value="...">
      <input name="tuid"  value="<user_id>">
      <input name="obtp"  value="3">              ← object type
      <input name="obid"  value="<post_id>">
      <input name="poid"  value="<post_id>">
      <input name="origin" value="9">
      <input name="rorigin" value="35">
      <textarea name="direct_response">
    </form>
"""

import re
import time
from typing import List, Dict, Optional
from datetime import datetime

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from config import Config
from utils.logger import Logger, pkt_stamp
from utils.helpers import strip_non_bmp
from core.sheets import SheetsManager


# ── DamaDam URLs ──────────────────────────────────────────────────────────────
_URL_INBOX    = f"{Config.BASE_URL}/inbox/"
_URL_ACTIVITY = f"{Config.BASE_URL}/inbox/activity/"

# ── Selectors ─────────────────────────────────────────────────────────────────
_SEL_ITEM_BLOCK     = "div.mbl.mtl"
_SEL_TID_BTN        = "button[name='tid']"
_SEL_NICK_BDI       = "div.cl.lsp.nos b bdi"
_SEL_MSG_SPAN       = "div.cl.lsp.nos span bdi"
_SEL_TIME_SPAN      = "span[style*='color:#999']"
_SEL_TYPE_SPAN      = "div.sp.cs.mrs span"
_SEL_REPLY_FORM     = "form[action*='/direct-response/send']"
_SEL_REPLY_TEXTAREA = "textarea[name='direct_response']"

# ── Activity Selectors (from Playwright) ───────────────────────────────────────
_SEL_ACTIVITY_BTN   = "button"  # Activity buttons like "POST ► ashi11-pk" - will filter by text
_SEL_ACTIVITY_TAB   = "button"
_SEL_REPLIES_TAB    = "button"
_SEL_POST_BTN       = "button"
_SEL_ACTIVITY_TEXT  = "button"  # Will filter by text content


def run_messages(driver, sheets: SheetsManager, logger: Logger) -> Dict:
    """
    Unified Message Mode: Sync conversations, activity, and send pending replies.
    Phase 1: Sync new conversations from /inbox/
    Phase 2: Fetch and log activity feed
    Phase 3: Send pending replies
    Returns stats dict.
    """
    import time as _time
    run_start = _time.time()

    logger.section("UNIFIED MESSAGE MODE")

    ws_queue = sheets.get_worksheet(Config.SHEET_MSG_QUE, headers=Config.MSG_QUE_COLS)
    ws_log = sheets.get_worksheet(Config.SHEET_MSG_LOG, headers=Config.MSG_LOG_COLS)
    if not ws_queue or not ws_log:
        logger.error("MsgQue or MsgLog sheet not found — run Setup first")
        return {}

    # ── Phase 1: Fetch inbox ──────────────────────────────────────────────────
    logger.info("Phase 1: Fetching inbox conversations...")
    inbox_items = _fetch_inbox(driver, logger)
    logger.info(f"Found {len(inbox_items)} conversations in inbox")

    all_queue_rows = sheets.read_all(ws_queue)
    queue_headers  = all_queue_rows[0] if all_queue_rows else Config.MSG_QUE_COLS
    queue_hmap     = SheetsManager.build_header_map(queue_headers)

    def qcell(row, *names):
        return SheetsManager.get_cell(row, queue_hmap, *names)

    existing_record_ids = {
        qcell(row, "RECORD_ID").lower()
        for row in all_queue_rows[1:]
        if qcell(row, "RECORD_ID")
    }

    new_synced = 0
    for item in inbox_items:
        record_id = _generate_record_id(item.get("tid", ""), item.get("nick", ""))
        nick = item.get("nick", "").strip()
        msg_date = _extract_date_from_time(item.get("time_str", ""))

        if not nick:
            continue

        # Log every inbox item to MessageLog (full history)
        _log_message_entry(sheets, ws_log, pkt_stamp(), record_id, nick,
                          item.get("type", ""), "IN", 
                          item.get("last_msg", ""), item.get("conv_url", ""), 
                          "Received", msg_date)

        # Sync new conversations into MessageQueue
        if record_id and record_id.lower() not in existing_record_ids:
            row_vals = [
                record_id,                    # RECORD_ID
                msg_date,                     # DATE
                nick,                         # NICK
                nick,                         # NAME (defaults to nick)
                item.get("type", ""),         # TYPE
                item.get("tid", ""),          # TID
                item.get("last_msg", ""),     # LAST_MESSAGE
                "",                           # MY_REPLY
                "Pending",                    # STATUS
                pkt_stamp(),                  # UPDATED
                "",                           # NOTES
            ]
            if sheets.append_row(ws_queue, row_vals):
                logger.ok(f"New conversation: [{item.get('type','')}] {nick} (record_id={record_id})")
                existing_record_ids.add(record_id.lower())
                new_synced += 1

    # ── Phase 2: Fetch activity ─────────────────────────────────────────────────
    logger.info("Phase 2: Fetching activity feed...")
    activities = _fetch_activity(driver, logger, sheets=sheets)
    logger.info(f"Found {len(activities)} activity items")

    for activity in activities:
        # Log activity using enhanced data structure
        _log_activity_entry(sheets, ws_log, activity)

    # ── Phase 3: Send pending replies ─────────────────────────────────────────
    logger.info("Phase 3: Sending pending replies...")

    all_queue_rows = sheets.read_all(ws_queue)
    queue_hmap     = SheetsManager.build_header_map(all_queue_rows[0]) if all_queue_rows else {}
    col_status     = sheets.get_col(all_queue_rows[0] if all_queue_rows else [], "STATUS")
    col_notes      = sheets.get_col(all_queue_rows[0] if all_queue_rows else [], "NOTES")
    col_updated    = sheets.get_col(all_queue_rows[0] if all_queue_rows else [], "UPDATED")

    def qcell2(row, *names):
        return SheetsManager.get_cell(row, queue_hmap, *names)

    pending_replies = []
    for i, row in enumerate(all_queue_rows[1:], start=2):
        reply  = qcell2(row, "MY_REPLY").strip()
        status = qcell2(row, "STATUS").lower()
        nick   = qcell2(row, "NICK").strip()
        tid    = qcell2(row, "TID").strip()
        if reply and status.startswith("pending"):
            pending_replies.append({
                "row": i, "nick": nick, "tid": tid, "reply": reply,
                "type": qcell2(row, "TYPE"),
            })

    # Build tid → conv_url from freshly fetched inbox items
    tid_to_url = {
        str(it.get("tid", "")): it.get("conv_url", "")
        for it in inbox_items if it.get("tid")
    }

    sent   = 0
    failed = 0

    for idx, item in enumerate(pending_replies, start=1):
        nick  = item["nick"]
        tid   = item["tid"]
        reply = item["reply"]
        row_n = item["row"]
        logger.info(f"[{idx}/{len(pending_replies)}] Replying to {nick} (tid={tid})")

        conv_url = (tid_to_url.get(tid) or "").strip()
        if not conv_url:
            conv_url = _URL_INBOX

        ok, sent_url = _send_reply(driver, conv_url, tid, reply, nick, logger)

        if ok:
            logger.ok(f"Reply sent → {nick}")
            sheets.update_row_cells(ws_queue, row_n, {
                col_status:  "Done",
                col_notes:   f"Replied @ {pkt_stamp()}",
                col_updated: pkt_stamp(),
            })
            record_id = _generate_record_id(tid, nick)
            _log_message_entry(sheets, ws_log, pkt_stamp(), record_id, nick,
                              item["type"], "OUT", reply, sent_url or conv_url, "Sent", 
                              _extract_date_from_time(""))
            sent += 1
        else:
            logger.warning(f"Reply failed → {nick}")
            sheets.update_row_cells(ws_queue, row_n, {
                col_status:  "Failed",
                col_notes:   f"Send failed @ {pkt_stamp()}",
                col_updated: pkt_stamp(),
            })
            record_id = _generate_record_id(tid, nick)
            _log_message_entry(sheets, ws_log, pkt_stamp(), record_id, nick,
                              item["type"], "OUT", reply, conv_url, "Failed",
                              _extract_date_from_time(""))
            failed += 1

        time.sleep(2)

    duration = _time.time() - run_start
    logger.section(
        f"MESSAGE MODE DONE — New:{new_synced}  Sent:{sent}  Failed:{failed}  Activities:{len(activities)}"
    )

    stats = {
        "new_synced":      new_synced,
        "sent":            sent,
        "replies_failed":  failed,
        "activities":      len(activities),
    }
    return stats


def _generate_record_id(tid: str, nick: str) -> str:
    """Generate a unique record ID combining TID and nickname."""
    if tid:
        return f"{tid}_{nick}"
    return f"NOID_{nick}"


def _extract_date_from_time(time_str: str) -> str:
    """Extract date from time string or return current date."""
    try:
        if "ago" in time_str.lower():
            return datetime.now().strftime("%Y-%m-%d")
        # Try to parse other formats if needed
        return datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.now().strftime("%Y-%m-%d")


# ════════════════════════════════════════════════════════════════════════════════
#  FETCH INBOX
# ════════════════════════════════════════════════════════════════════════════════

def _fetch_inbox(driver, logger: Logger) -> List[Dict]:
    """Open /inbox/ and parse all visible conversation blocks."""
    try:
        driver.get(_URL_INBOX)
        time.sleep(3)

        items:      List[Dict] = []
        seen_tids:  set        = set()
        seen_nicks: set        = set()

        blocks = driver.find_elements(By.CSS_SELECTOR, _SEL_ITEM_BLOCK)
        if not blocks:
            logger.warning("No inbox blocks found — inbox may be empty or session expired")
            return []

        for block in blocks[:50]:
            try:
                item = _parse_inbox_block(block)
                if not item:
                    continue

                tid  = str(item.get("tid",  "")).strip()
                nick = str(item.get("nick", "")).strip()

                if not nick:
                    continue
                if tid and tid in seen_tids:
                    continue
                if not tid and nick.lower() in seen_nicks:
                    continue

                if tid:
                    seen_tids.add(tid)
                seen_nicks.add(nick.lower())
                items.append(item)

            except Exception as e:
                logger.debug(f"Skipped inbox block: {e}")
                continue

        return items

    except Exception as e:
        logger.error(f"Inbox fetch error: {e}")
        return []


def _parse_inbox_block(block) -> Optional[Dict]:
    """Parse one div.mbl.mtl inbox block into a structured dict."""
    # TID from button[name='tid']
    tid = ""
    try:
        btn = block.find_elements(By.CSS_SELECTOR, _SEL_TID_BTN)
        if btn:
            tid = (btn[0].get_attribute("value") or "").strip()
    except Exception:
        pass

    # Conversation type
    conv_type = ""
    try:
        type_spans = block.find_elements(By.CSS_SELECTOR, _SEL_TYPE_SPAN)
        if type_spans:
            raw = (type_spans[0].text or "").strip().upper()
            if "1" in raw and "ON" in raw:
                conv_type = "1ON1"
            elif "POST" in raw:
                conv_type = "POST"
            elif "MEHFIL" in raw:
                conv_type = "MEHFIL"
            else:
                conv_type = raw[:20]
    except Exception:
        pass

    # Nickname
    nick = ""
    try:
        nick_els = block.find_elements(By.CSS_SELECTOR, _SEL_NICK_BDI)
        if nick_els:
            nick = (nick_els[0].text or "").strip()
    except Exception:
        pass

    if not nick:
        return None

    # Last message
    last_msg = ""
    try:
        msg_els = block.find_elements(By.CSS_SELECTOR, _SEL_MSG_SPAN)
        if msg_els:
            last_msg = (msg_els[0].text or "").strip()
    except Exception:
        pass

    # Time string
    time_str = ""
    try:
        time_els = block.find_elements(By.CSS_SELECTOR, _SEL_TIME_SPAN)
        if time_els:
            time_str = (time_els[0].text or "").strip()
    except Exception:
        pass

    # Conversation URL
    conv_url = _URL_INBOX
    try:
        links = block.find_elements(
            By.CSS_SELECTOR,
            "a[href*='/comments/'], a[href*='/content/'], a[href*='/inbox/']"
        )
        for a in links:
            href = (a.get_attribute("href") or "").strip()
            if href and href != _URL_INBOX:
                conv_url = href if href.startswith("http") else f"{Config.BASE_URL}{href}"
                break
    except Exception:
        pass

    return {
        "tid":       tid,
        "nick":      nick,
        "type":      conv_type,
        "last_msg":  last_msg,
        "time_str":  time_str,
        "timestamp": pkt_stamp(),
        "conv_url":  conv_url,
    }


# ════════════════════════════════════════════════════════════════════════════════
#  SEND REPLY
# ════════════════════════════════════════════════════════════════════════════════

def _send_reply(driver, conv_url: str, tid: str,
                reply_text: str, nick: str, logger: Logger):
    """
    Navigate to the conversation and submit a reply.
    Returns (success: bool, posted_url: str)
    """
    safe_reply = strip_non_bmp(reply_text)[:350]

    def _try_send(page_url: str):
        """Try to send reply on a given page. Returns (ok, url) or (None, None) if no form."""
        try:
            driver.get(page_url)
            time.sleep(3)

            forms = driver.find_elements(By.CSS_SELECTOR, _SEL_REPLY_FORM)
            for form in forms:
                try:
                    textarea = form.find_element(By.CSS_SELECTOR, _SEL_REPLY_TEXTAREA)
                except Exception:
                    continue

                # Find submit button
                submit_btn = None
                for sel in (
                    "button[name='dec'][value='1']",
                    "button[type='submit']",
                    "input[type='submit']",
                ):
                    try:
                        btns = form.find_elements(By.CSS_SELECTOR, sel)
                        if btns:
                            submit_btn = btns[0]
                            break
                    except Exception:
                        pass

                if not submit_btn:
                    continue

                # Type using send_keys (React-safe)
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});"
                    "arguments[0].focus();"
                    "arguments[0].value = '';",
                    textarea
                )
                time.sleep(0.3)
                try:
                    textarea.clear()
                except Exception:
                    pass
                time.sleep(0.2)
                textarea.send_keys(safe_reply)
                time.sleep(0.4)

                # Submit
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", submit_btn
                )
                time.sleep(0.2)
                driver.execute_script("arguments[0].click();", submit_btn)
                time.sleep(3)

                return True, driver.current_url

            return None, None  # No form found on this page
        except Exception as e:
            logger.debug(f"_try_send error on {page_url}: {e}")
            return False, None

    # Attempt 1: go to the conversation URL
    ok, url = _try_send(conv_url)
    if ok is True:
        return True, url
    if ok is False:
        return False, None

    # ok is None — no form found. Try /inbox/ as fallback
    logger.debug(f"No reply form at {conv_url} — trying /inbox/ fallback for {nick}")
    ok2, url2 = _try_send(_URL_INBOX)
    if ok2 is True:
        return True, url2

    logger.warning(f"Reply form not found for {nick} (tid={tid})")
    return False, None


# ════════════════════════════════════════════════════════════════════════════════
#  FETCH ACTIVITY
# ════════════════════════════════════════════════════════════════════════════════

def _fetch_activity(driver, logger: Logger, sheets: SheetsManager,
                    max_items: int = 60, max_pages: int = 5) -> List[Dict]:
    """Fetch DamaDam activity feed from /inbox/activity/ with enhanced data extraction."""
    items: List[Dict] = []
    seen:  set         = set()

    try:
        # Navigate to activity page
        driver.get(_URL_ACTIVITY)
        time.sleep(3)
        
        # Try to click ACTIVITY tab if available
        try:
            activity_buttons = driver.find_elements(By.CSS_SELECTOR, _SEL_ACTIVITY_TAB)
            activity_tab = None
            for btn in activity_buttons:
                if "ACTIVITY" in btn.text.upper():
                    activity_tab = btn
                    break
            
            if activity_tab:
                activity_tab.click()
                time.sleep(2)
        except Exception:
            logger.info("ACTIVITY tab not found or not clickable, continuing with current view")

        for page_num in range(1, max_pages + 1):
            if len(items) >= max_items:
                break

            # Handle pagination if needed
            if page_num > 1:
                try:
                    driver.get(f"{_URL_ACTIVITY}?page={page_num}")
                    time.sleep(3)
                except Exception:
                    break

            # Extract activity buttons and filter by text content
            all_buttons = driver.find_elements(By.CSS_SELECTOR, _SEL_ACTIVITY_BTN)
            activity_buttons = []
            
            # Filter buttons that contain activity-related text
            for btn in all_buttons:
                btn_text = btn.text.strip().upper()
                if any(keyword in btn_text for keyword in ["POST", "REPLIED", "LIKED", "COMMENTED", "FOLLOWED"]):
                    activity_buttons.append(btn)
            
            if not activity_buttons:
                # Fallback to original selector
                activity_buttons = driver.find_elements(By.CSS_SELECTOR, _SEL_ITEM_BLOCK)
                
            if not activity_buttons:
                break

            # Refresh the page reference to avoid stale elements
            for i in range(len(activity_buttons)):
                if len(items) >= max_items:
                    break
                    
                try:
                    # Re-find elements to avoid stale references
                    all_current_buttons = driver.find_elements(By.CSS_SELECTOR, _SEL_ACTIVITY_BTN)
                    current_buttons = []
                    
                    # Filter buttons again
                    for btn in all_current_buttons:
                        btn_text = btn.text.strip().upper()
                        if any(keyword in btn_text for keyword in ["POST", "REPLIED", "LIKED", "COMMENTED", "FOLLOWED"]):
                            current_buttons.append(btn)
                    
                    if i >= len(current_buttons):
                        break
                        
                    button = current_buttons[i]
                    
                    # Extract button text and attributes
                    button_text = button.text.strip()
                    button_value = button.get_attribute("value") or ""
                    
                    # Skip empty buttons
                    if not button_text:
                        continue
                    
                    # Parse activity information from button text
                    activity_data = _parse_activity_button(button_text, button_value)
                    if not activity_data:
                        continue
                    
                    # Create unique identifier for duplicate prevention
                    activity_id = f"{activity_data['type']}_{activity_data['post_key']}_{activity_data['name_key']}"
                    
                    # Check for duplicates using ScrapeState
                    if _check_activity_duplicate(sheets, activity_id):
                        continue
                    
                    # Save to ScrapeState to prevent future duplicates
                    _save_activity_state(sheets, activity_id)
                    
                    # Get additional details if needed
                    try:
                        # Re-find and filter buttons again for click
                        all_click_buttons = driver.find_elements(By.CSS_SELECTOR, _SEL_ACTIVITY_BTN)
                        click_buttons = []
                        
                        for btn in all_click_buttons:
                            btn_text = btn.text.strip().upper()
                            if any(keyword in btn_text for keyword in ["POST", "REPLIED", "LIKED", "COMMENTED", "FOLLOWED"]):
                                click_buttons.append(btn)
                        
                        if i < len(click_buttons):
                            button = click_buttons[i]
                            button.click()
                            time.sleep(1)
                            current_url = driver.current_url
                            activity_data['url'] = current_url
                            # Go back to activity page
                            driver.back()
                            time.sleep(1)
                    except Exception:
                        activity_data['url'] = _URL_ACTIVITY
                    
                    items.append(activity_data)
                    
                except Exception as e:
                    logger.info(f"Error processing activity button: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error fetching activity: {e}")

    logger.info(f"Found {len(items)} activity items")
    return items


def _parse_activity_button(button_text: str, button_value: str) -> Optional[Dict]:
    """Parse activity button text to extract structured data."""
    try:
        # Parse button text like "POST ► ashi11-pk: post removed" or "POST ► pic Nimra-Mughal104:"
        parts = button_text.split('►')
        if len(parts) < 2:
            return None
        
        activity_type = parts[0].strip().upper()  # POST, REPLIED, LIKED
        rest = parts[1].strip()
        
        # Extract name and post details
        name_key = ""
        post_key = ""
        description = ""
        
        if ':' in rest:
            name_part, desc_part = rest.split(':', 1)
            name_key = name_part.strip()
            description = desc_part.strip()
            
            # Extract post key from button value or generate one
            if button_value:
                post_key = button_value
            else:
                post_key = f"{activity_type}_{name_key}_{hash(description) % 10000}"
        else:
            name_key = rest
            description = ""
            post_key = f"{activity_type}_{name_key}_{hash(button_text) % 10000}"
        
        return {
            'type': activity_type,
            'name_key': name_key,
            'post_key': post_key,
            'description': description,
            'button_text': button_text,
            'timestamp': pkt_stamp(),
            'date': pkt_stamp().split(' ')[0]
        }
        
    except Exception:
        return None


def _check_activity_duplicate(sheets: SheetsManager, activity_id: str) -> bool:
    """Check if activity already exists in ScrapeState to prevent duplicates."""
    try:
        ws_state = sheets.get_worksheet(Config.SHEET_SCRAPE_STATE, headers=Config.SCRAPE_STATE_COLS)
        if not ws_state:
            return False
            
        existing_data = sheets.read_all(ws_state)
        if len(existing_data) < 2:
            return False
            
        headers = existing_data[0]
        key_col = sheets.get_col(headers, "KEY")
        value_col = sheets.get_col(headers, "VALUE")
        
        for row in existing_data[1:]:
            if len(row) > max(key_col, value_col):
                key = row[key_col].strip()
                if key == f"activity_{activity_id}":
                    return True
        
        return False
        
    except Exception:
        return False


def _save_activity_state(sheets: SheetsManager, activity_id: str):
    """Save activity ID to ScrapeState to prevent future duplicates."""
    try:
        ws_state = sheets.get_worksheet(Config.SHEET_SCRAPE_STATE, headers=Config.SCRAPE_STATE_COLS)
        if not ws_state:
            return
            
        sheets.append_row(ws_state, [
            f"activity_{activity_id}",  # KEY
            "processed",                 # VALUE
            pkt_stamp()                  # UPDATED
        ])
        
    except Exception:
        pass


# ════════════════════════════════════════════════════════════════════════════════
#  LOG HELPERS
# ════════════════════════════════════════════════════════════════════════════════

def _log_message_entry(sheets: SheetsManager, ws_log,
                      timestamp: str, record_id: str, nick: str,
                      conv_type: str, direction: str,
                      message: str, url: str, status: str, date: str):
    """Append one row to MessageLog sheet with date organization."""
    sheets.append_row(ws_log, [
        date,        # DATE - for sorting and organization
        timestamp,   # TIMESTAMP
        record_id,   # RECORD_ID - person record ID
        nick,        # NICK
        conv_type,   # TYPE
        direction,   # DIRECTION
        message,     # MESSAGE
        url,         # CONV_URL
        status,      # STATUS
    ])


def _log_activity_entry(sheets: SheetsManager, ws_log, activity_data: Dict):
    """Log activity entry with enhanced data structure."""
    try:
        record_id = f"ACTIVITY_{activity_data['post_key']}_{activity_data['name_key']}"
        message = f"{activity_data['type']}: {activity_data['description']}"
        
        _log_message_entry(
            sheets=sheets,
            ws_log=ws_log,
            timestamp=activity_data['timestamp'],
            record_id=record_id,
            nick=activity_data['name_key'],
            conv_type=activity_data['type'],
            direction="ACTIVITY",
            message=message,
            url=activity_data.get('url', ''),
            status="Logged",
            date=activity_data['date']
        )
        
    except Exception as e:
        logger.info(f"Error logging activity entry: {e}")
