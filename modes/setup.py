"""
modes/setup.py — DD-Msg-Bot V5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Setup Mode: Create the 4-sheet structure + apply formatting.
  MsgQue   — outbound message targets
  MsgLog   — sent message history
  Inbox    — inbox conversations (one row per NICK)
  InboxLog — complete inbox + activity history

Old sheet names are deleted on fresh setup.
"""

from config import Config
from utils.logger import Logger
from core.sheets import SheetsManager


_OLD_SHEETS = [
    "MsgList", "MsgQue", "MsgLog",
    "PostQueue", "PostQue", "PostLog",
    "InboxQueue", "InboxQue", "InboxLog",
    "MessageQueue", "MessageLog",
    "MasterLog", "Logs", "ScrapeState",
    "Dashboard", "RunLog", "Sheet1", "Inbox",
]


def run(sheets: SheetsManager, logger: Logger):
    """
    Fresh setup:
      1. Delete old/legacy sheets
      2. Create 4 new sheets with correct headers + formatting
    """
    logger.section("SETUP MODE — V5.0 Structure")

    # ── Step 1: Delete old sheets ─────────────────────────────────────────────
    logger.info("Removing old sheets...")
    try:
        existing = [ws.title for ws in sheets._wb.worksheets()]
    except Exception as e:
        logger.warning(f"Could not list worksheets: {e}")
        existing = []

    for name in _OLD_SHEETS:
        if name in existing:
            try:
                ws = sheets._wb.worksheet(name)
                sheets._wb.del_worksheet(ws)
                logger.ok(f"  Deleted: {name}")
            except Exception as e:
                logger.warning(f"  Could not delete '{name}': {e}")

    # ── Step 2: Create new sheets ─────────────────────────────────────────────
    logger.info("Creating sheets...")
    for sheet_name, col_headers in Config.ALL_SHEETS.items():
        ws = sheets.get_worksheet(sheet_name, create_if_missing=True, headers=col_headers)
        if ws:
            sheets.ensure_headers(ws, col_headers)
            logger.ok(f"  {sheet_name} — ready ({len(col_headers)} cols)")
        else:
            logger.error(f"  Failed to create: {sheet_name}")

    # ── Step 3: Apply formatting ──────────────────────────────────────────────
    logger.info("Applying formatting...")
    try:
        _apply_format(sheets, logger)
    except Exception as e:
        logger.warning(f"Formatting skipped: {e}")

    logger.section("SETUP COMPLETE — 4 sheets ready")
    logger.info("Order: MsgQue → MsgLog → Inbox → InboxLog")
    logger.info("")
    logger.info("VLOOKUP reminder for MsgQue cols D,E,F,G (row 3 example):")
    logger.info('  D (CITY):      =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),3,FALSE),"")')
    logger.info('  E (POSTS):     =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),6,FALSE),"")')
    logger.info('  F (FOLLOWERS): =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),8,FALSE),"")')
    logger.info('  G (GENDER):    =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),4,FALSE),"")')


def _apply_format(sheets: SheetsManager, logger: Logger):
    """Apply Lexend font + dark header to all 4 sheets."""
    try:
        from googleapiclient.discovery import build
        gc      = sheets.client
        creds   = gc.http_client.auth
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.warning(f"Sheets API v4 unavailable: {e}")
        return

    HEADER_BG   = {"red": 0.149, "green": 0.196, "blue": 0.220}
    HEADER_TEXT = {"red": 1.0,   "green": 1.0,   "blue": 1.0}

    for sheet_name, col_headers in Config.ALL_SHEETS.items():
        if not col_headers:
            continue
        try:
            ws = sheets.get_worksheet(sheet_name, create_if_missing=False)
            if not ws:
                continue
            sheet_id  = ws.id
            col_count = len(col_headers)

            requests = [
                # All cells: Lexend 8, centered, clip
                {"repeatCell": {
                    "range": {"sheetId": sheet_id},
                    "cell": {"userEnteredFormat": {
                        "textFormat": {"fontFamily": "Lexend", "fontSize": 8},
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment":   "MIDDLE",
                        "wrapStrategy":        "CLIP",
                    }},
                    "fields": "userEnteredFormat(textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
                }},
                # Header row: dark bg, white text
                {"repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0, "endRowIndex": 1,
                        "startColumnIndex": 0, "endColumnIndex": col_count,
                    },
                    "cell": {"userEnteredFormat": {
                        "backgroundColor": HEADER_BG,
                        "textFormat": {
                            "fontFamily": "Lexend", "fontSize": 8,
                            "bold": True, "foregroundColor": HEADER_TEXT,
                        },
                        "horizontalAlignment": "CENTER",
                        "verticalAlignment":   "MIDDLE",
                        "wrapStrategy":        "CLIP",
                    }},
                    "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,verticalAlignment,wrapStrategy)",
                }},
                # Freeze row 1
                {"updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }},
            ]

            service.spreadsheets().batchUpdate(
                spreadsheetId=Config.SHEET_ID,
                body={"requests": requests},
            ).execute()
            logger.ok(f"  {sheet_name} formatted")

        except Exception as e:
            logger.warning(f"  {sheet_name} format error: {e}")
