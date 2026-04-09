"""
main.py — DD-Msg-Bot V5.0
━━━━━━━━━━━━━━━━━━━━━━━━━
Entry point. Clean 3-option menu.

  1. Send Messages  → reads MsgQue, sends to targets
  2. Inbox Sync     → syncs inbox + activity, sends pending replies
  3. Setup Sheets   → creates/recreates the 4-sheet structure
  0. Exit

CLI (GitHub Actions):
  python main.py msg      → Message Mode
  python main.py inbox    → Inbox Mode
  python main.py setup    → Setup Sheets
"""

import sys
import argparse

from config import Config
from utils.logger import Logger
from core.browser import BrowserManager
from core.login import LoginManager
from core.sheets import SheetsManager

import modes.message  as message_mode
import modes.messages as messages_mode


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def _build_parser():
    p = argparse.ArgumentParser(
        prog="main.py",
        description=f"DD-Msg-Bot V{Config.VERSION} — DamaDam.pk automation",
    )
    p.add_argument("mode", nargs="?",
                   choices=["msg", "messages", "setup"],
                   help="Mode to run (omit for interactive menu)")
    p.add_argument("--max",      dest="max_items", type=int, default=0,
                   metavar="N", help="Max items to process (0=unlimited)")
    p.add_argument("--debug",    action="store_true", help="Verbose debug logging")
    p.add_argument("--headless", action="store_true", default=None,
                   help="Force headless browser")
    return p


# ═══════════════════════════════════════════════════════════════════════════════
#  Interactive Menu
# ═══════════════════════════════════════════════════════════════════════════════

_MENU = r"""
  ╔══════════════════════════════════════════════╗
  ║      DD-Msg-Bot V5.0  —  DamaDam.pk         ║
  ╠══════════════════════════════════════════════╣
  ║                                              ║
  ║   1.  Send Messages  (MsgQue targets)        ║
  ║   2.  Inbox Sync     (Inbox + Activity)      ║
  ║   3.  Setup Sheets   (Create / Recreate)     ║
  ║                                              ║
  ║   0.  Exit                                   ║
  ╚══════════════════════════════════════════════╝
"""

def _menu() -> tuple:
    print(_MENU)
    while True:
        raw = input("  Choice: ").strip()
        mode_map = {"1": "msg", "2": "inbox", "3": "setup", "0": None}
        if raw not in mode_map:
            print("  Enter 1, 2, 3, or 0.\n")
            continue

        mode = mode_map[raw]
        if mode is None:
            print("  Goodbye!\n")
            sys.exit(0)

        max_items = 0
        if mode in ("msg",):
            lim = input("  Max items (Enter = unlimited): ").strip()
            if lim.isdigit():
                max_items = int(lim)

        return mode, max_items


# ═══════════════════════════════════════════════════════════════════════════════
#  Runners
# ═══════════════════════════════════════════════════════════════════════════════

def _run_with_browser(mode: str, max_n: int) -> None:
    logger = Logger(mode)
    logger.section(f"DD-Msg-Bot V{Config.VERSION} — {mode.upper()} MODE")
    Config.validate()

    bm     = BrowserManager(logger)
    driver = bm.start()
    if not driver:
        logger.error("Browser failed to start")
        sys.exit(1)

    try:
        lm = LoginManager(driver, logger)
        if not lm.login():
            logger.error("Login failed")
            sys.exit(1)

        sheets = SheetsManager(logger)
        if not sheets.connect():
            logger.error("Google Sheets connection failed")
            sys.exit(1)

        if mode == "msg":
            message_mode.run(driver, sheets, logger, max_targets=max_n)
        elif mode == "messages":
            messages_mode.run(driver, sheets, logger)

    finally:
        bm.close()


def _run_setup() -> None:
    from modes.setup import run as setup_run
    logger = Logger("setup")
    logger.section("SETUP MODE")
    Config.validate()
    sheets = SheetsManager(logger)
    if not sheets.connect():
        logger.error("Google Sheets connection failed")
        sys.exit(1)
    setup_run(sheets, logger)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = _build_parser()
    args   = parser.parse_args()

    if getattr(args, "debug", False):
        Config.DEBUG = True
    if getattr(args, "headless", None):
        Config.HEADLESS = True

    mode = args.mode

    if not mode:
        if Config.IS_CI:
            parser.error("mode required in CI (msg | inbox | setup)")
        mode, max_n = _menu()
        args.max_items = max_n

    max_n = getattr(args, "max_items", 0)

    if mode == "setup":
        _run_setup()
    elif mode in ("msg", "inbox"):
        _run_with_browser(mode, max_n)
    else:
        parser.error(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
