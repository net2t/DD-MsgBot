"""
config.py — DD-Msg-Bot V2
━━━━━━━━━━━━━━━━━━━━━━━━━
All configuration, constants, sheet names, and column definitions.
All settings come from environment variables (or .env file).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# ── Load .env file if present ──────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent.absolute()
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:
    """All runtime settings, loaded from environment variables."""

    # ── DamaDam Credentials ────────────────────────────────────────────────────
    DD_NICK  = os.getenv("DD_LOGIN_EMAIL",  "").strip()  # DamaDam username/nick
    DD_PASS  = os.getenv("DD_LOGIN_PASS",   "").strip()
    DD_NICK2 = os.getenv("DD_LOGIN_EMAIL2", "").strip()  # Backup account (optional)
    DD_PASS2 = os.getenv("DD_LOGIN_PASS2",  "").strip()

    # ── Google Sheets ──────────────────────────────────────────────────────────
    SHEET_ID         = os.getenv("DD_SHEET_ID", "").strip()
    CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", "credentials.json").strip()
    CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()

    # ── Browser ────────────────────────────────────────────────────────────────
    CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH", "").strip()
    HEADLESS          = os.getenv("DD_HEADLESS", "1").strip().lower() in {"1", "true", "yes"}
    DISABLE_IMAGES    = os.getenv("DD_DISABLE_IMAGES", "1").strip().lower() in {"1", "true", "yes"}
    PAGE_LOAD_TIMEOUT = int(os.getenv("DD_PAGE_LOAD_TIMEOUT", "60") or "60")

    # ── Cookie file for session persistence ────────────────────────────────────
    COOKIE_FILE = str(SCRIPT_DIR / "damadam_cookies.pkl")

    # ── Run Flags ──────────────────────────────────────────────────────────────
    DRY_RUN      = os.getenv("DD_DRY_RUN", "0").strip().lower() in {"1", "true", "yes"}
    DEBUG        = os.getenv("DD_DEBUG",   "0").strip() == "1"
    MAX_PROFILES = int(os.getenv("DD_MAX_PROFILES", "0") or "0")

    # ── GitHub Actions detection ───────────────────────────────────────────────
    IS_CI = bool(os.getenv("GITHUB_ACTIONS"))

    # ── URLs ───────────────────────────────────────────────────────────────────
    BASE_URL  = "https://damadam.pk"
    LOGIN_URL = "https://damadam.pk/login/"
    HOME_URL  = "https://damadam.pk/"

    # ── Message Mode ──────────────────────────────────────────────────────────
    MAX_POST_PAGES    = int(os.getenv("DD_MAX_POST_PAGES",    "3") or "3")
    MSG_DELAY_SECONDS = float(os.getenv("DD_MSG_DELAY_SECONDS", "3") or "3")

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_DIR = SCRIPT_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    # ── Bot Version ────────────────────────────────────────────────────────────
    VERSION = "4.1.0"

    # ════════════════════════════════════════════════════════════════════════════
    #  SHEET NAMES
    #  These must match the tab names in your Google Spreadsheet exactly.
    # ════════════════════════════════════════════════════════════════════════════

    # Queue sheets  — bot reads from these to know what to do
    SHEET_MSG_QUE = "MsgQue"         # Unified queue (inbox sync + pending replies)
    SHEET_MESSAGE_QUEUE = "MessageQueue"  # Original message queue sheet
    SHEET_INBOX_QUE = "InboxQue"     # Inbox queue sheet

    # Log sheets    — bot writes results here after each action
    SHEET_MSG_LOG = "MsgLog"         # Unified log (inbox events + activity + sent replies)
    SHEET_MESSAGE_LOG = "MessageLog"    # Original message log sheet
    SHEET_LOGS = "Logs"               # Master activity log
    SHEET_INBOX_LOG = "InboxLog"      # Inbox log sheet

    # State sheets  — pagination cursors and state
    SHEET_SCRAPE_STATE = "ScrapeState"  # Pagination cursor storage
    SHEET_DASHBOARD = "Dashboard"     # Summary/analysis sheet
    SHEET_RUN_LOG = "RunLog"          # Run history and statistics

    # ── Keep old names as aliases so existing code doesn't break ──────────────
    SHEET_MSG_LIST    = SHEET_MSG_QUE          # backwards compat alias
    SHEET_INBOX_QUE   = SHEET_MSG_QUE          # backwards compat alias
    SHEET_INBOX_LOG   = SHEET_MSG_LOG          # backwards compat alias
    SHEET_MESSAGE_QUEUE = "MessageQueue"       # original message queue
    SHEET_MESSAGE_LOG   = "MessageLog"         # original message log
    SHEET_LOGS          = "Logs"                # master activity log
    SHEET_MASTER_LOG    = SHEET_MSG_LOG        # backwards compat alias
    SHEET_SCRAPE_STATE  = "ScrapeState"        # state storage
    SHEET_DASHBOARD     = "Dashboard"          # analysis sheet

    # ════════════════════════════════════════════════════════════════════════════
    #  COLUMN DEFINITIONS — single source of truth for every sheet
    # ════════════════════════════════════════════════════════════════════════════

    # ── MsgQue — unified message queue (replaces InboxQue/MessageQueue) ─────────
    #  Bot syncs new conversations here. You fill MY_REPLY. Bot sends it.
    MSG_QUE_COLS = [
        "RECORD_ID",    # A  Unique record ID (TID_NICK or NOID_NICK)
        "DATE",         # B  Date of conversation (YYYY-MM-DD)
        "NICK",         # C  DamaDam username
        "NAME",         # D  Display name
        "TYPE",         # E  1ON1 / POST / MEHFIL / UNKNOWN
        "TID",          # F  DamaDam user ID (tid from button value)
        "LAST_MESSAGE", # G  Last message received
        "MY_REPLY",     # H  Your reply text — bot sends this when STATUS=Pending
        "STATUS",       # I  Pending → Done / Failed / NoReply
        "UPDATED",      # J  Timestamp of last sync
        "NOTES",        # K  Set by bot
    ]

    # ── MsgLog — unified message log (replaces InboxLog/MessageLog/Logs) ───────
    #  One row per message event or activity item. Complete history organized by date.
    MSG_LOG_COLS = [
        "DATE",        # A  Date of message (YYYY-MM-DD) - for sorting
        "TIMESTAMP",   # B  PKT timestamp
        "RECORD_ID",   # C  Person record ID (TID_NICK or NOID_NICK)
        "NICK",        # D  Username
        "TYPE",        # E  1ON1 / POST / MEHFIL / ACTIVITY
        "DIRECTION",   # F  IN / OUT / ACTIVITY
        "MESSAGE",     # G  Message text or activity description
        "CONV_URL",    # H  Link to the conversation or post
        "STATUS",      # I  Received / Sent / Failed / Logged
    ]

    # ── MessageQueue — Original message queue sheet ─────────────────────────────
    MESSAGE_QUEUE_COLS = [
        "MODE",        # A  Nick or URL
        "NAME",        # B  Display name (your reference)
        "NICK",        # C  DamaDam username or profile URL
        "CITY",        # D  Scraped city (read-only)
        "POSTS",       # E  Scraped post count (read-only)
        "FOLLOWERS",   # F  Scraped follower count (read-only)
        "GENDER",      # G  Scraped gender (read-only)
        "MESSAGE",     # H  Message text — supports {{name}}, {{city}} placeholders
        "STATUS",      # I  Pending → Done / Skipped / Failed
        "NOTES",       # J  Set by bot after each run
        "RESULT",      # K  URL of the post where message was sent
        "SENT_MSG",    # L  Actual resolved message that was sent
    ]

    # ── MessageLog — Original message log sheet ────────────────────────────────
    MESSAGE_LOG_COLS = [
        "TIMESTAMP",   # A  PKT timestamp
        "NICK",        # B  Username
        "NAME",        # C  Display name
        "MESSAGE",     # D  Message text
        "POST_URL",    # E  URL of the post
        "STATUS",      # F  Sent / Failed / Skipped
        "NOTES",       # G  Additional notes
    ]

    # ── Logs — Master activity log sheet ───────────────────────────────────────
    LOGS_COLS = [
        "TIMESTAMP",   # A  PKT timestamp
        "MODE",        # B  Mode name
        "ACTION",      # C  Action performed
        "NICK",        # D  Username
        "URL",         # E  Related URL
        "STATUS",      # F  Status
        "DETAILS",     # G  Additional details
    ]

    # ── ScrapeState — Pagination cursor storage ───────────────────────────────
    SCRAPE_STATE_COLS = [
        "KEY",         # A  State key
        "VALUE",       # B  State value
        "UPDATED",     # C  Last update timestamp
    ]

    # ── Backwards compat aliases for column lists ──────────────────────────────
    MSG_LIST_COLS   = MSG_QUE_COLS
    INBOX_COLS      = MSG_QUE_COLS
    INBOX_QUE_COLS  = MSG_QUE_COLS
    INBOX_LOG_COLS  = MSG_LOG_COLS
    LOGS_COLS       = MSG_LOG_COLS
    MASTER_LOG_COLS = MSG_LOG_COLS

    # ════════════════════════════════════════════════════════════════════════════
    #  All sheets in setup order
    # ════════════════════════════════════════════════════════════════════════════
    ALL_SHEETS = {
        SHEET_MSG_QUE: MSG_QUE_COLS,
        SHEET_MSG_LOG: MSG_LOG_COLS,
        SHEET_MESSAGE_QUEUE: MESSAGE_QUEUE_COLS,
        SHEET_MESSAGE_LOG: MESSAGE_LOG_COLS,
        SHEET_LOGS: LOGS_COLS,
        SHEET_SCRAPE_STATE: SCRAPE_STATE_COLS,
        SHEET_DASHBOARD: [],  # Dashboard has no predefined columns
    }

    @classmethod
    def validate(cls):
        """Validate required settings. Exits if critical values are missing."""
        errors = []
        if not cls.DD_NICK:
            errors.append("DD_LOGIN_EMAIL (DamaDam username) is required")
        if not cls.DD_PASS:
            errors.append("DD_LOGIN_PASS is required")
        if not cls.SHEET_ID:
            errors.append("DD_SHEET_ID (Google Sheets ID) is required")
        has_json = bool(cls.CREDENTIALS_JSON)
        has_file = (Path(cls.CREDENTIALS_FILE).exists()
                    or (SCRIPT_DIR / cls.CREDENTIALS_FILE).exists())
        if not has_json and not has_file:
            errors.append(
                f"Google credentials not found. "
                f"Need {cls.CREDENTIALS_FILE} or GOOGLE_CREDENTIALS_JSON env var."
            )
        if errors:
            print("=" * 60)
            for e in errors:
                print(f"[CONFIG ERROR] {e}")
            print("=" * 60)
            sys.exit(1)
        return True

    @classmethod
    def get_credentials_path(cls):
        """Return absolute path to credentials.json."""
        p = Path(cls.CREDENTIALS_FILE)
        if p.is_absolute() and p.exists():
            return str(p)
        return str(SCRIPT_DIR / cls.CREDENTIALS_FILE)
