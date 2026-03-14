"""
modes/setup.py — DD-Msg-Bot V2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Setup Mode: Create and format all required sheets in the Google Spreadsheet.
Run this once when setting up a new sheet, or to repair/reset headers.
No browser needed.
"""

from config import Config
from utils.logger import Logger
from core.sheets import SheetsManager


# Map of sheet name → expected column headers
_SHEETS_TO_SETUP = {
    Config.SHEET_MSG_LIST:   Config.MSG_LIST_COLS,
    Config.SHEET_POST_QUEUE: Config.POST_QUEUE_COLS,
    Config.SHEET_MASTER_LOG: Config.MASTER_LOG_COLS,
    Config.SHEET_INBOX:      Config.INBOX_COLS,
}


def run(sheets: SheetsManager, logger: Logger):
    """
    Create all required sheets and ensure headers are correct.
    Existing data rows are never deleted — only the header row is checked/fixed.
    """
    logger.section("SETUP MODE")

    for sheet_name, col_headers in _SHEETS_TO_SETUP.items():
        logger.info(f"Checking: {sheet_name}")

        # Get or create the worksheet
        ws = sheets.get_worksheet(sheet_name, create_if_missing=True,
                                   headers=col_headers)
        if not ws:
            logger.error(f"Could not create/access: {sheet_name}")
            continue

        # Ensure headers match the expected column definitions
        sheets.ensure_headers(ws, col_headers)
        logger.ok(f"{sheet_name} — OK ({len(col_headers)} columns)")

    logger.section("SETUP COMPLETE — All sheets ready")


def run_format(sheets: SheetsManager, logger: Logger):
    """
    Apply consistent visual formatting to all sheets:
      - Font:              Lexend
      - Horizontal align:  CENTER for all cells
      - Vertical align:    MIDDLE for all cells
      - Text wrapping:     CLIP (no overflow, no wrap)
      - Header row (row 1): Dark background (#263238), white text, bold
      - Data rows start at row 2 (row 1 is always the header)

    Uses Google Sheets API v4 batchUpdate for efficiency.
    All 4 sheets are formatted in a single API call per sheet.
    """
    logger.section("FORMAT MODE")

    import gspread
    from googleapiclient.discovery import build  # type: ignore

    # ── Get the raw Google Sheets service (v4 API) ─────────────────────────
    # gspread wraps gspread.Client.auth which holds a google.auth Credentials object.
    # We build the sheets v4 service directly from those credentials.
    try:
        gc     = sheets.client                    # gspread.Client
        creds  = gc.auth                          # google.oauth2 Credentials
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error(f"Could not build Sheets API service: {e}")
        return

    spreadsheet_id = Config.SHEET_ID

    # ── Colour constants ────────────────────────────────────────────────────
    # Header background: dark blue-grey #263238
    HEADER_BG   = {"red": 0.149, "green": 0.196, "blue": 0.220}
    # Header text:  white
    HEADER_TEXT = {"red": 1.0,   "green": 1.0,   "blue": 1.0}

    sheet_names = list(_SHEETS_TO_SETUP.keys())

    for sheet_name in sheet_names:
        logger.info(f"Formatting: {sheet_name}")

        # ── Get the sheet's numeric sheetId ──────────────────────────────
        try:
            ws       = sheets.get_worksheet(sheet_name)
            sheet_id = ws.id   # numeric gspread worksheet id
        except Exception as e:
            logger.warning(f"Cannot access {sheet_name}: {e}")
            continue

        col_count = len(_SHEETS_TO_SETUP[sheet_name])  # number of columns

        requests = [

            # ── 1. Set font for ALL cells (entire sheet) ────────────────
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,          # row 1 onwards
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "textFormat":           {"fontFamily": "Lexend", "fontSize": 10},
                            "horizontalAlignment":  "CENTER",
                            "verticalAlignment":    "MIDDLE",
                            "wrapStrategy":         "CLIP",
                        }
                    },
                    "fields": (
                        "userEnteredFormat(textFormat,horizontalAlignment,"
                        "verticalAlignment,wrapStrategy)"
                    ),
                }
            },

            # ── 2. Header row (row 0 = row 1 in Sheets): dark bg, white bold text ──
            {
                "repeatCell": {
                    "range": {
                        "sheetId":       sheet_id,
                        "startRowIndex": 0,   # row 1 (0-indexed)
                        "endRowIndex":   1,   # only row 1
                        "startColumnIndex": 0,
                        "endColumnIndex":   col_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": HEADER_BG,
                            "textFormat": {
                                "fontFamily":  "Lexend",
                                "fontSize":    10,
                                "bold":        True,
                                "foregroundColor": HEADER_TEXT,
                            },
                            "horizontalAlignment": "CENTER",
                            "verticalAlignment":   "MIDDLE",
                            "wrapStrategy":        "CLIP",
                        }
                    },
                    "fields": (
                        "userEnteredFormat(backgroundColor,textFormat,"
                        "horizontalAlignment,verticalAlignment,wrapStrategy)"
                    ),
                }
            },

            # ── 3. Freeze header row so it stays visible when scrolling ──
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            },

        ]

        # ── Send batchUpdate for this sheet ──────────────────────────────
        try:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={"requests": requests},
            ).execute()
            logger.ok(f"{sheet_name} — formatted")
        except Exception as e:
            logger.error(f"{sheet_name} format failed: {e}")

    logger.section("FORMAT COMPLETE — All sheets styled with Lexend font")
