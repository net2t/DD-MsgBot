"""
config.py — DD-Msg-Bot V5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━
Minimal 4-sheet structure:
  1. MsgQue   — outbound message targets (you fill, bot sends)
  2. MsgLog   — log of every sent message
  3. Inbox    — inbox sync queue + reply col (one row per NICK, no duplicates)
  4. InboxLog — complete history of all inbox events + activity

VLOOKUP columns (D=CITY, E=POSTS, F=FOLLOWERS, G=GENDER) are preserved
in MsgQue. Bot never touches those columns — user puts VLOOKUP formulas there.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent.absolute()
env_path = SCRIPT_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


class Config:

    # ── Credentials ────────────────────────────────────────────────────────────
    DD_NICK  = os.getenv("DD_LOGIN_EMAIL",  "").strip()
    DD_PASS  = os.getenv("DD_LOGIN_PASS",   "").strip()
    DD_NICK2 = os.getenv("DD_LOGIN_EMAIL2", "").strip()
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
    COOKIE_FILE       = str(SCRIPT_DIR / "damadam_cookies.pkl")

    # ── Run Flags ──────────────────────────────────────────────────────────────
    DRY_RUN = os.getenv("DD_DRY_RUN", "0").strip().lower() in {"1", "true", "yes"}
    DEBUG   = os.getenv("DD_DEBUG",   "0").strip() == "1"
    IS_CI   = bool(os.getenv("GITHUB_ACTIONS"))

    # ── URLs ───────────────────────────────────────────────────────────────────
    BASE_URL  = "https://damadam.pk"
    LOGIN_URL = "https://damadam.pk/login/"
    HOME_URL  = "https://damadam.pk/"

    # ── Timing ─────────────────────────────────────────────────────────────────
    MAX_POST_PAGES    = int(os.getenv("DD_MAX_POST_PAGES",    "3") or "3")
    MSG_DELAY_SECONDS = float(os.getenv("DD_MSG_DELAY_SECONDS", "3") or "3")

    # ── Logging ────────────────────────────────────────────────────────────────
    LOG_DIR = SCRIPT_DIR / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    VERSION = "5.0.0"

    # ════════════════════════════════════════════════════════════════════════════
    #  SHEET NAMES  — exactly 4 sheets
    # ════════════════════════════════════════════════════════════════════════════

    SHEET_MSG_QUE   = "MsgQue"    # Outbound message targets
    SHEET_MSG_LOG   = "MsgLog"    # Sent message history
    SHEET_INBOX     = "Inbox"     # Inbox conversations + reply queue (keyed by NICK)
    SHEET_INBOX_LOG = "InboxLog"  # All inbox events + activity (append-only history)

    # ════════════════════════════════════════════════════════════════════════════
    #  COLUMN DEFINITIONS
    # ════════════════════════════════════════════════════════════════════════════

    # ── MsgQue ─────────────────────────────────────────────────────────────────
    # D,E,F,G are user-managed VLOOKUP formula columns. Bot reads them but
    # never writes to them. IMPORTRANGE from Profiles sheet:
    #   D (CITY)      = col 3
    #   E (POSTS)     = col 6
    #   F (FOLLOWERS) = col 8
    #   G (GENDER)    = col 4
    MSG_QUE_COLS = [
        "MODE",       # A  Nick / URL
        "NAME",       # B  Display name (your reference)
        "NICK",       # C  DamaDam username or profile URL
        "CITY",       # D  VLOOKUP → IMPORTRANGE col 3  (bot never writes)
        "POSTS",      # E  VLOOKUP → IMPORTRANGE col 6  (bot never writes)
        "FOLLOWERS",  # F  VLOOKUP → IMPORTRANGE col 8  (bot never writes)
        "GENDER",     # G  VLOOKUP → IMPORTRANGE col 4  (bot never writes)
        "MESSAGE",    # H  Template — supports {{name}} {{city}} {{gender}} etc.
        "STATUS",     # I  Pending → Done / Skipped / Failed / NoPosts / NotFollowing
        "NOTES",      # J  Bot writes reason + timestamp here
        "RESULT",     # K  URL of the post where message was sent
        "SENT_MSG",   # L  Resolved message text actually sent
    ]

    # ── MsgLog ─────────────────────────────────────────────────────────────────
    MSG_LOG_COLS = [
        "DATE",       # A  YYYY-MM-DD
        "TIMESTAMP",  # B  PKT timestamp
        "NICK",       # C  Target username
        "NAME",       # D  Display name
        "POST_URL",   # E  URL of post where message was sent
        "STATUS",     # F  Sent / Failed / Skipped / NoPosts / NotFollowing
        "NOTES",      # G  Reason or extra detail
        "MESSAGE",    # H  Message text that was sent
    ]

    # ── Inbox ──────────────────────────────────────────────────────────────────
    # One row per unique NICK. Bot upserts (updates existing row or adds new).
    # User fills MY_REPLY col, bot sends it and marks STATUS=Done.
    # No duplicates — NICK is the unique key.
    INBOX_COLS = [
        "NICK",       # A  DamaDam username — unique key, no duplicates
        "TID",        # B  DamaDam internal user ID (stable)
        "TYPE",       # C  1ON1 / POST / MEHFIL
        "LAST_MSG",   # D  Last message received from this person
        "DATE",       # E  Date of last message (YYYY-MM-DD)
        "TIME_STR",   # F  Relative time ("2 hours ago")
        "MY_REPLY",   # G  Your reply — bot sends when STATUS=Pending
        "STATUS",     # H  New / Pending / Done / Failed
        "CONV_URL",   # I  Link to conversation
        "UPDATED",    # J  Last sync timestamp
        "NOTES",      # K  Bot notes
    ]

    # ── InboxLog ───────────────────────────────────────────────────────────────
    # Append-only complete history. Every inbox sync row + every activity item.
    INBOX_LOG_COLS = [
        "DATE",       # A  YYYY-MM-DD (for date-sorting)
        "TIMESTAMP",  # B  PKT timestamp
        "NICK",       # C  Username
        "TID",        # D  User ID
        "TYPE",       # E  1ON1 / POST / MEHFIL / ACTIVITY
        "DIRECTION",  # F  IN / OUT / ACTIVITY
        "MESSAGE",    # G  Message text or activity description
        "CONV_URL",   # H  Link to conversation or post
        "STATUS",     # I  Received / Sent / Failed / Logged
    ]

    # ── Setup order ────────────────────────────────────────────────────────────
    ALL_SHEETS = {
        SHEET_MSG_QUE:   MSG_QUE_COLS,
        SHEET_MSG_LOG:   MSG_LOG_COLS,
        SHEET_INBOX:     INBOX_COLS,
        SHEET_INBOX_LOG: INBOX_LOG_COLS,
    }

    @classmethod
    def validate(cls):
        errors = []
        if not cls.DD_NICK:
            errors.append("DD_LOGIN_EMAIL is required")
        if not cls.DD_PASS:
            errors.append("DD_LOGIN_PASS is required")
        if not cls.SHEET_ID:
            errors.append("DD_SHEET_ID is required")
        has_json = bool(cls.CREDENTIALS_JSON)
        has_file = (Path(cls.CREDENTIALS_FILE).exists()
                    or (SCRIPT_DIR / cls.CREDENTIALS_FILE).exists())
        if not has_json and not has_file:
            errors.append(
                f"Credentials not found. Need {cls.CREDENTIALS_FILE} "
                f"or GOOGLE_CREDENTIALS_JSON env var."
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
        p = Path(cls.CREDENTIALS_FILE)
        if p.is_absolute() and p.exists():
            return str(p)
        return str(SCRIPT_DIR / cls.CREDENTIALS_FILE)
