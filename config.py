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

    # ── Post Mode ─────────────────────────────────────────────────────────────
    POST_COOLDOWN_SECONDS = int(os.getenv("DD_POST_COOLDOWN_SECONDS", "135") or "135")
    POST_CAPTION_MAX_LEN  = int(os.getenv("DD_POST_CAPTION_MAX_LEN",  "300") or "300")
    POST_TAGS_MAX_LEN     = int(os.getenv("DD_POST_TAGS_MAX_LEN",     "120") or "120")
    POST_MAX_REPEAT_CHARS = int(os.getenv("DD_POST_MAX_REPEAT_CHARS",   "6") or "6")
    POST_SIGNATURE        = os.getenv("DD_POST_SIGNATURE", "").strip()

    # ── Rekhta Mode ───────────────────────────────────────────────────────────
    REKHTA_URL         = os.getenv("DD_REKHTA_URL", "https://www.rekhta.org/shayari-image")
    REKHTA_MAX_SCROLLS = int(os.getenv("DD_REKHTA_MAX_SCROLLS", "6") or "6")

    # ── Image Download ────────────────────────────────────────────────────────
    IMAGE_DOWNLOAD_TIMEOUT = int(os.getenv("DD_IMAGE_DOWNLOAD_TIMEOUT", "90") or "90")
    IMAGE_DOWNLOAD_RETRIES = int(os.getenv("DD_IMAGE_DOWNLOAD_RETRIES",  "3") or "3")

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
    SHEET_MSG_QUE      = "MsgQue"         # Message targets queue
    SHEET_MESSAGE_QUEUE = "MessageQueue"   # Unified message queue (replaces InboxQue)

    # Log sheets    — bot writes results here after each action
    SHEET_MSG_LOG      = "MsgLog"         # Every message sent (history per target)
    SHEET_MESSAGE_LOG  = "MessageLog"     # Unified message log (replaces InboxLog)

    # Master log    — one row per any action across all modes
    SHEET_LOGS         = "Logs"

    # Scrape state  — pagination cursor so Mode 1 resumes instead of re-scanning
    SHEET_SCRAPE_STATE = "ScrapeState"

    # Dashboard     — summary/analysis (formulas only, bot never writes here)
    SHEET_DASHBOARD = "Dashboard"

    # ── Keep old names as aliases so existing code doesn't break ──────────────
    SHEET_MASTER_LOG = SHEET_LOGS              # backwards compat alias
    SHEET_MSG_LIST   = SHEET_MSG_QUE           # backwards compat alias
    SHEET_INBOX_QUE  = SHEET_MESSAGE_QUEUE     # backwards compat alias
    SHEET_INBOX_LOG  = SHEET_MESSAGE_LOG       # backwards compat alias

    # ════════════════════════════════════════════════════════════════════════════
    #  COLUMN DEFINITIONS — single source of truth for every sheet
    # ════════════════════════════════════════════════════════════════════════════

    # ── MsgQue — message targets queue ────────────────────────────────────────
    #  You fill this in. Bot reads it, sends messages, updates STATUS/NOTES/RESULT.
    MSG_QUE_COLS = [
        "MODE",       # A  Nick / URL
        "NAME",       # B  Display name (your reference)
        "NICK",       # C  DamaDam username or profile URL
        "CITY",       # D  Scraped city       (read-only reference)
        "POSTS",      # E  Scraped post count  (read-only reference)
        "FOLLOWERS",  # F  Scraped followers   (read-only reference)
        "GENDER",     # G  Scraped gender      (read-only reference)
        "MESSAGE",    # H  Template text — supports {{name}}, {{city}} placeholders
        "STATUS",     # I  Pending → Done / Skipped / Failed
        "NOTES",      # J  Set by bot
        "RESULT",     # K  URL of post where message was sent
        "SENT_MSG",   # L  Actual resolved message that was sent (set by bot)
    ]

    # ── MsgLog — one row per message sent ─────────────────────────────────────
    #  Bot appends here after every successful or failed message attempt.
    MSG_LOG_COLS = [
        "TIMESTAMP",  # A  PKT timestamp
        "NICK",       # B  Target username
        "NAME",       # C  Display name
        "MESSAGE",    # D  Message text that was sent
        "POST_URL",   # E  URL of post the message was sent on
        "STATUS",     # F  Sent / Failed / Skipped
        "NOTES",      # G  Error or extra detail
    ]

    # ── MessageQueue — unified message queue (replaces InboxQue) ───────────────────
    #  Bot syncs new conversations here. You fill MY_REPLY. Bot sends it.
    MESSAGE_QUEUE_COLS = [
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

    # ── MessageLog — unified message log (replaces InboxLog) ───────────────────────
    #  One row per message event or activity item. Complete history organized by date.
    MESSAGE_LOG_COLS = [
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

    # ── Logs — master log (one row per any bot action) ─────────────────────────
    LOGS_COLS = [
        "TIMESTAMP",  # A
        "MODE",       # B
        "ACTION",     # C
        "NICK",       # D
        "URL",        # E
        "STATUS",     # F
        "DETAILS",    # G
    ]

    # ── RunLog — one row per complete bot run ─────────────────────────────────
    RUN_LOG_COLS = [
        "TIMESTAMP",  # A  When the run started (PKT)
        "MODE",       # B  Which mode was run (rekhta/msg/post/inbox/setup)
        "STATUS",     # C  Done / Failed / Stopped
        "ADDED",      # D  Items added    (Rekhta: new rows in PostQue)
        "POSTED",     # E  Posts created  (Post mode)
        "SENT",       # F  Messages sent  (Msg / Inbox reply)
        "FAILED",     # G  Failures
        "SKIPPED",    # H  Skipped rows
        "DURATION",   # I  How long the run took (seconds)
        "NOTES",      # J  Extra info or error summary
    ]

    # ── ScrapeState — key/value store for pagination cursors ──────────────────
    SCRAPE_STATE_COLS = [
        "KEY",        # A  State key (e.g. "rekhta_last_page")
        "VALUE",      # B  State value
        "UPDATED",    # C  When this value was last written
    ]

    # ── Backwards compat aliases for column lists ──────────────────────────────
    MSG_LIST_COLS       = MSG_QUE_COLS
    MASTER_LOG_COLS     = LOGS_COLS
    INBOX_COLS          = MESSAGE_QUEUE_COLS
    INBOX_QUE_COLS      = MESSAGE_QUEUE_COLS   # backwards compat
    INBOX_LOG_COLS      = MESSAGE_LOG_COLS     # backwards compat

    # ════════════════════════════════════════════════════════════════════════════
    #  All sheets in setup order
    # ════════════════════════════════════════════════════════════════════════════
    ALL_SHEETS = {
        SHEET_MSG_QUE:         MSG_QUE_COLS,
        SHEET_MESSAGE_QUEUE:   MESSAGE_QUEUE_COLS,
        SHEET_MSG_LOG:         MSG_LOG_COLS,
        SHEET_MESSAGE_LOG:     MESSAGE_LOG_COLS,
        SHEET_LOGS:            LOGS_COLS,
        SHEET_SCRAPE_STATE:    SCRAPE_STATE_COLS,
        # Dashboard has no fixed columns — it's formula-based, created empty
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
