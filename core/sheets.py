"""
core/sheets.py — DD-Msg-Bot V5.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Google Sheets connection and all read/write operations.
"""

import json
import time
from pathlib import Path
from typing import Optional, List, Dict

import gspread
from gspread.exceptions import WorksheetNotFound, APIError
from google.oauth2.service_account import Credentials

from config import Config
from utils.logger import Logger, pkt_stamp


_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


class SheetsManager:

    def __init__(self, logger: Logger):
        self.log    = logger
        self.client = None
        self._wb    = None

    # ════════════════════════════════════════════════════════════════════════════
    #  Connection
    # ════════════════════════════════════════════════════════════════════════════

    def connect(self) -> bool:
        try:
            self.log.info("Connecting to Google Sheets...")
            creds = None
            if Config.CREDENTIALS_JSON:
                data = json.loads(Config.CREDENTIALS_JSON)
                pk = data.get("private_key", "")
                if isinstance(pk, str) and "\\n" in pk:
                    data["private_key"] = pk.replace("\\n", "\n")
                creds = Credentials.from_service_account_info(data, scopes=_SCOPES)
            else:
                cred_path = Config.get_credentials_path()
                if not Path(cred_path).exists():
                    self.log.error(f"credentials.json not found: {cred_path}")
                    return False
                creds = Credentials.from_service_account_file(cred_path, scopes=_SCOPES)

            self.client = gspread.authorize(creds)
            self._wb    = self.client.open_by_key(Config.SHEET_ID)
            self.log.ok("Google Sheets connected")
            return True
        except Exception as e:
            self.log.error(f"Sheets connection failed: {e}")
            return False

    # ════════════════════════════════════════════════════════════════════════════
    #  Worksheet helpers
    # ════════════════════════════════════════════════════════════════════════════

    def get_worksheet(self, name: str, create_if_missing: bool = True,
                      headers: Optional[List[str]] = None):
        try:
            return self._wb.worksheet(name)
        except WorksheetNotFound:
            if not create_if_missing:
                self.log.warning(f"Worksheet '{name}' not found")
                return None
            return self._create_worksheet(name, headers)
        except Exception as e:
            self.log.error(f"get_worksheet('{name}') error: {e}")
            return None

    def _create_worksheet(self, name: str, headers: Optional[List[str]] = None):
        try:
            ws = self._wb.add_worksheet(title=name, rows=1000, cols=20)
            if headers:
                ws.update("A1", [headers])
                self._format_header_row(ws, len(headers))
            self.log.ok(f"Created worksheet: {name}")
            return ws
        except Exception as e:
            self.log.error(f"Could not create worksheet '{name}': {e}")
            return None

    def _format_header_row(self, ws, num_cols: int):
        """Dark header row + freeze."""
        try:
            ws.format("1:1", {
                "backgroundColor":  {"red": 0.149, "green": 0.196, "blue": 0.220},
                "textFormat":       {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER",
            })
            self._wb.batch_update({"requests": [{
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": ws.id,
                        "gridProperties": {"frozenRowCount": 1},
                    },
                    "fields": "gridProperties.frozenRowCount",
                }
            }]})
        except Exception:
            pass

    # ════════════════════════════════════════════════════════════════════════════
    #  Column resolution
    # ════════════════════════════════════════════════════════════════════════════

    @staticmethod
    def get_col(headers: List[str], *names: str) -> Optional[int]:
        norm = [str(h).strip().upper() for h in headers]
        for name in names:
            key = str(name).strip().upper()
            if key in norm:
                return norm.index(key) + 1
        return None

    @staticmethod
    def build_header_map(headers: List[str]) -> Dict[str, int]:
        return {str(h).strip().upper(): i for i, h in enumerate(headers)}

    @staticmethod
    def get_cell(row: List[str], header_map: Dict[str, int], *names: str) -> str:
        for name in names:
            key = str(name).strip().upper()
            if key in header_map:
                idx = header_map[key]
                if 0 <= idx < len(row):
                    val = str(row[idx]).strip()
                    if val:
                        return val
        return ""

    # ════════════════════════════════════════════════════════════════════════════
    #  Read
    # ════════════════════════════════════════════════════════════════════════════

    def read_all(self, ws) -> List[List[str]]:
        if not ws:
            return []
        try:
            return ws.get_all_values()
        except Exception as e:
            self.log.error(f"read_all failed on '{ws.title}': {e}")
            return []

    def read_col_values(self, ws, col_num: int) -> List[str]:
        if not ws:
            return []
        try:
            col_data = ws.col_values(col_num)
            return [str(v).strip() for v in col_data[1:] if v]
        except Exception as e:
            self.log.error(f"read_col_values failed: {e}")
            return []

    # ════════════════════════════════════════════════════════════════════════════
    #  Write (with retry)
    # ════════════════════════════════════════════════════════════════════════════

    def update_cell(self, ws, row: int, col: int, value: str,
                    retries: int = 3) -> bool:
        if Config.DRY_RUN:
            self.log.dry_run(f"update_cell r={row} c={col} → '{value}'")
            return True
        for attempt in range(1, retries + 1):
            try:
                ws.update_cell(row, col, value)
                return True
            except APIError as e:
                if attempt < retries:
                    wait = 2 ** attempt
                    self.log.warning(f"API error (attempt {attempt}), retry in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    self.log.error(f"update_cell failed: {e}")
                    return False
            except Exception as e:
                self.log.error(f"update_cell error: {e}")
                return False
        return False

    def update_row_cells(self, ws, row: int, updates: Dict[int, str],
                         retries: int = 3) -> bool:
        if not updates:
            return True
        if Config.DRY_RUN:
            self.log.dry_run(f"update_row_cells r={row} updates={updates}")
            return True
        from gspread.utils import rowcol_to_a1
        data = [{"range": rowcol_to_a1(row, col), "values": [[val]]}
                for col, val in updates.items()]
        for attempt in range(1, retries + 1):
            try:
                ws.batch_update(data)
                return True
            except APIError as e:
                if attempt < retries:
                    wait = 2 ** attempt
                    self.log.warning(f"batch update error, retry in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    self.log.error(f"update_row_cells failed: {e}")
                    return False
            except Exception as e:
                self.log.error(f"update_row_cells error: {e}")
                return False
        return False

    def append_row(self, ws, values: List, retries: int = 3) -> bool:
        if Config.DRY_RUN:
            self.log.dry_run(f"append_row → {values}")
            return True
        for attempt in range(1, retries + 1):
            try:
                ws.append_row(values, value_input_option="USER_ENTERED")
                return True
            except APIError as e:
                if attempt < retries:
                    wait = 2 ** attempt
                    self.log.warning(f"append_row API error, retry in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    self.log.error(f"append_row failed: {e}")
                    return False
            except Exception as e:
                self.log.error(f"append_row error: {e}")
                return False
        return False

    # ════════════════════════════════════════════════════════════════════════════
    #  Ensure headers
    # ════════════════════════════════════════════════════════════════════════════

    def ensure_headers(self, ws, expected_cols: List[str]) -> bool:
        if not ws:
            return False
        try:
            current = ws.row_values(1)
            current_upper  = [str(h).strip().upper() for h in current]
            expected_upper = [str(h).strip().upper() for h in expected_cols]
            if current_upper[:len(expected_upper)] != expected_upper:
                self.log.info(f"Updating headers on '{ws.title}'")
                ws.update("A1", [expected_cols])
                self._format_header_row(ws, len(expected_cols))
            return True
        except Exception as e:
            self.log.error(f"ensure_headers failed on '{ws.title}': {e}")
            return False
