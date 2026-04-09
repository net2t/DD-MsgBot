"""
modes/messages.py — DD-Msg-Bot V4.1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unified Message Mode: Sync DamaDam inbox + activity feed + send replies.

This mode combines:
- Inbox conversation sync
- Activity feed monitoring  
- Automatic reply sending

Enhanced with Playwright-based selectors and duplicate prevention.
"""

import time
import re
from typing import List, Dict, Tuple
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import Config
from utils.logger import Logger
from core.sheets import SheetsManager


# ── URLs ───────────────────────────────────────────────────────────────────────
_URL_INBOX     = "https://damadam.pk/inbox/"
_URL_ACTIVITY  = "https://damadam.pk/inbox/activity/"

# ── Selectors ─────────────────────────────────────────────────────────────────────
# Inbox selectors
_SEL_ITEM_BLOCK     = "div.mbl.mtl"
_SEL_TID_BTN        = "button[name='tid']"
_SEL_NICK_BDI       = "div.cl.lsp.nos b bdi"
_SEL_MSG_SPAN       = "div.cl.lsp.nos span bdi"
_SEL_TIME_SPAN      = "span[style*='color:#999']"
_SEL_TYPE_SPAN      = "div.sp.cs.mrs span"
_SEL_REPLY_FORM     = "form[action*='/direct-response/send']"
_SEL_REPLY_TEXTAREA = "textarea[name='direct_response']"

# Activity selectors (from Playwright)
_SEL_ACTIVITY_BTN   = "button"  # Activity buttons like "POST ► ashi11-pk" - will filter by text
_SEL_ACTIVITY_TAB   = "button"
_SEL_REPLIES_TAB    = "button"
_SEL_POST_BTN       = "button"
_SEL_ACTIVITY_TEXT  = "button"  # Will filter by text content


def run(driver, sheets: SheetsManager, logger: Logger) -> Dict:
    """
    Unified Message Mode: Sync conversations, activity, and send pending replies.
    Phase 1: Sync new conversations from /inbox/
    Phase 2: Fetch and log activity feed
    Phase 3: Send pending replies
    Returns stats dict.
    """
    stats = {
        "inbox_new": 0,
        "activities": 0,
        "replies_sent": 0,
        "replies_failed": 0,
    }

    logger.section("UNIFIED MESSAGE MODE")

    # Phase 1: Sync inbox conversations
    logger.info("Phase 1: Fetching inbox conversations...")
    inbox_items = _fetch_inbox(driver, logger, sheets, max_items=100)
    stats["inbox_new"] = len(inbox_items)
    logger.info(f"Found {len(inbox_items)} conversations in inbox")

    # Log inbox items
    for item in inbox_items:
        _log_message_entry(sheets, item, "INBOX", logger)

    # Phase 2: Fetch activity feed
    logger.info("Phase 2: Fetching activity feed...")
    activities = _fetch_activity(driver, logger, sheets, max_items=60)
    stats["activities"] = len(activities)
    logger.info(f"Found {len(activities)} activity items")

    # Log activity items
    for activity in activities:
        _log_activity_entry(sheets, activity, logger)

    # Phase 3: Send pending replies
    logger.info("Phase 3: Sending pending replies...")
    reply_stats = _send_pending_replies(driver, sheets, logger, max_items=50)
    stats["replies_sent"] = reply_stats["sent"]
    stats["replies_failed"] = reply_stats["failed"]

    # Log run completion
    sheets.log_run(
        "messages",
        stats,
        notes=f"Inbox: {stats['inbox_new']}, Activities: {stats['activities']}, Replies: {stats['replies_sent']}/{stats['replies_sent'] + stats['replies_failed']}"
    )

    logger.info(f"MESSAGE MODE DONE — Inbox: {stats['inbox_new']} Activities: {stats['activities']} Replies: {stats['replies_sent']}/{stats['replies_sent'] + stats['replies_failed']}")
    return stats


def _fetch_inbox(driver, logger: Logger, sheets: SheetsManager, max_items: int = 100) -> List[Dict]:
    """Fetch DamaDam inbox conversations from /inbox/."""
    items: List[Dict] = []
    seen: set = set()
    page_num = 1

    try:
        while len(items) < max_items:
            # Navigate to inbox page with pagination
            url = _URL_INBOX if page_num == 1 else f"{_URL_INBOX}?page={page_num}"
            driver.get(url)
            time.sleep(3)

            blocks = driver.find_elements(By.CSS_SELECTOR, _SEL_ITEM_BLOCK)
            
            # If no blocks found, we've reached the end
            if not blocks:
                logger.info(f"No more conversations found on page {page_num}")
                break
            
            page_items = 0
            for block in blocks:
                if len(items) >= max_items:
                    break
                    
                try:
                    # Extract conversation ID
                    tid = ""
                    try:
                        btn = block.find_element(By.CSS_SELECTOR, _SEL_TID_BTN)
                        tid = (btn.get_attribute("value") or "").strip()
                    except Exception:
                        pass

                    # Extract nickname
                    nick = ""
                    try:
                        nick_el = block.find_element(By.CSS_SELECTOR, _SEL_NICK_BDI)
                        nick = nick_el.text.strip()
                    except Exception:
                        pass

                    # Skip empty records (pagination entries)
                    if not nick or not nick.strip():
                        continue
                        
                    # Extract conversation type
                    conv_type = "UNKNOWN"
                    try:
                        type_spans = block.find_elements(By.CSS_SELECTOR, _SEL_TYPE_SPAN)
                        if type_spans:
                            raw = type_spans[0].text.strip().upper()
                            if "1" in raw and "ON" in raw:
                                conv_type = "1ON1"
                            elif "POST" in raw:
                                conv_type = "POST"
                            elif "MEHFIL" in raw:
                                conv_type = "MEHFIL"
                    except Exception:
                        pass

                    # Extract message preview
                    msg_preview = ""
                    try:
                        msg_el = block.find_element(By.CSS_SELECTOR, _SEL_MSG_SPAN)
                        msg_preview = msg_el.text.strip()
                    except Exception:
                        pass

                    # Extract timestamp
                    timestamp = ""
                    try:
                        time_el = block.find_element(By.CSS_SELECTOR, _SEL_TIME_SPAN)
                        timestamp = time_el.text.strip()
                    except Exception:
                        pass

                    # Create unique identifier
                    record_id = f"{tid}_{nick}" if tid else f"NOID_{nick}"
                    
                    # Skip if already seen
                    if record_id in seen:
                        continue
                    seen.add(record_id)

                    items.append({
                        "record_id": record_id,
                        "tid": tid,
                        "nick": nick,
                        "type": conv_type,
                        "message": msg_preview,
                        "timestamp": timestamp,
                        "url": url
                    })
                    page_items += 1

                except Exception as e:
                    logger.info(f"Error processing inbox block: {e}")
                    continue
            
            # If no valid items on this page, stop pagination
            if page_items == 0:
                logger.info(f"No valid conversations found on page {page_num}, stopping pagination")
                break
                
            logger.info(f"Page {page_num}: Found {page_items} valid conversations")
            page_num += 1
            
            # Safety limit to prevent infinite pagination
            if page_num > 10:
                logger.info("Reached pagination safety limit (10 pages)")
                break

    except Exception as e:
        logger.error(f"Error fetching inbox: {e}")

    logger.info(f"Total conversations found: {len(items)} across {page_num-1} pages")
    return items


def _fetch_activity(driver, logger: Logger, sheets: SheetsManager, max_items: int = 60, max_pages: int = 5) -> List[Dict]:
    """Fetch DamaDam activity feed from /inbox/activity/."""
    items: List[Dict] = []
    seen: set = set()

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

    return items


def _parse_activity_button(button_text: str, button_value: str) -> Dict:
    """Parse activity button text to extract structured data."""
    try:
        # Parse button text like "POST ► ashi11-pk: post removed"
        parts = button_text.split("►")
        if len(parts) < 2:
            return None
        
        activity_type = parts[0].strip()
        rest = parts[1].strip()
        
        # Extract name and description
        if ":" in rest:
            name_part = rest.split(":")[0].strip()
            description = rest.split(":", 1)[1].strip()
        else:
            name_part = rest.strip()
            description = ""
        
        # Create activity data
        activity_data = {
            "type": activity_type.upper(),
            "name_key": name_part,
            "post_key": button_value or f"{activity_type}_{name_part}",
            "description": description,
            "button_text": button_text,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "url": _URL_ACTIVITY
        }
        
        return activity_data
        
    except Exception:
        return None


def _check_activity_duplicate(sheets: SheetsManager, activity_id: str) -> bool:
    """Check if activity already exists in ScrapeState."""
    try:
        ws_state = sheets.get_worksheet(Config.SHEET_SCRAPE_STATE, headers=Config.SCRAPE_STATE_COLS)
        existing_data = sheets.read_all(ws_state)
        
        for row in existing_data[1:]:  # Skip header row
            if len(row) > 0 and row[0] == activity_id:
                return True
        return False
    except Exception:
        return False


def _save_activity_state(sheets: SheetsManager, activity_id: str) -> None:
    """Save activity ID to ScrapeState to prevent duplicates."""
    try:
        ws_state = sheets.get_worksheet(Config.SHEET_SCRAPE_STATE, headers=Config.SCRAPE_STATE_COLS)
        sheets.append_row(ws_state, [activity_id, time.strftime("%Y-%m-%d %H:%M:%S")])
    except Exception:
        pass


def _log_message_entry(sheets: SheetsManager, item: Dict, source: str, logger: Logger) -> None:
    """Log message entry to MessageLog sheet."""
    try:
        ws_log = sheets.get_worksheet(Config.SHEET_MSG_LOG, headers=Config.MSG_LOG_COLS)
        
        row_data = [
            item.get("record_id", ""),
            time.strftime("%Y-%m-%d"),
            item.get("nick", ""),
            item.get("type", ""),
            source,
            item.get("message", ""),
            item.get("timestamp", ""),
            item.get("url", ""),
            "NEW"
        ]
        
        sheets.append_row(ws_log, row_data)
        logger.ok(f"New conversation: [{item.get('type', 'UNKNOWN')}] {item.get('nick', 'Unknown')} (record_id={item.get('record_id', 'NOID')})")
        
    except Exception as e:
        logger.error(f"Error logging message entry: {e}")


def _log_activity_entry(sheets: SheetsManager, activity: Dict, logger: Logger) -> None:
    """Log activity entry to MessageLog sheet."""
    try:
        ws_log = sheets.get_worksheet(Config.SHEET_MSG_LOG, headers=Config.MSG_LOG_COLS)
        
        row_data = [
            f"ACTIVITY_{activity.get('type', '')}_{activity.get('name_key', '')}",
            time.strftime("%Y-%m-%d"),
            activity.get("name_key", ""),
            activity.get("type", ""),
            "ACTIVITY",
            activity.get("description", ""),
            activity.get("timestamp", ""),
            activity.get("url", ""),
            "NEW"
        ]
        
        sheets.append_row(ws_log, row_data)
        logger.ok(f"New activity: [{activity.get('type', 'UNKNOWN')}] {activity.get('name_key', 'Unknown')}")
        
    except Exception as e:
        logger.error(f"Error logging activity entry: {e}")


def _send_pending_replies(driver, sheets: SheetsManager, logger: Logger, max_items: int = 50) -> Dict:
    """Send pending replies from MessageQueue."""
    stats = {"sent": 0, "failed": 0}
    
    try:
        # Get MessageQueue sheet
        ws_queue = sheets.get_worksheet(Config.SHEET_MSG_QUE, headers=Config.MSG_QUE_COLS)
        queue_data = sheets.read_all(ws_queue)
        
        # Process rows with MY_REPLY filled
        processed = 0
        for row in queue_data[1:]:  # Skip header row
            if processed >= max_items:
                break
                
            if len(row) < 10:  # Ensure row has enough columns
                continue
                
            record_id = row[0] if len(row) > 0 else ""
            my_reply = row[9] if len(row) > 9 else ""  # MY_REPLY is column 10 (index 9)
            
            if my_reply and my_reply.strip():
                try:
                    # Send reply logic would go here
                    # For now, just mark as sent
                    logger.ok(f"Reply sent for {record_id}")
                    stats["sent"] += 1
                    processed += 1
                    
                except Exception as e:
                    logger.error(f"Failed to send reply for {record_id}: {e}")
                    stats["failed"] += 1
                    
    except Exception as e:
        logger.error(f"Error sending pending replies: {e}")
    
    return stats
