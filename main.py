"""
main.py — DD-Msg-Bot V2 - Focused Version
━━━━━━━━━━━━━━━━━━━━━━━
Entry point for 3 core bot modes.

CLI usage (GitHub Actions / direct):
    python main.py msg            → Message Mode
    python main.py inbox          → Inbox Mode
    python main.py activity       → Activity Mode

Options:
    --max N    Process only N items (0 = unlimited)
    --debug    Verbose debug logging
    --headless Force headless browser

Local interactive menu:
    python main.py
    (no arguments — shows a numbered menu)
"""

import sys
import os
import argparse

from config import Config
from utils.logger import Logger
from core.browser import BrowserManager
from core.login import LoginManager
from core.sheets import SheetsManager

import modes.message  as message_mode
import modes.inbox    as inbox_mode


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI Argument Parser
# ═══════════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    """Define all CLI arguments."""
    p = argparse.ArgumentParser(
        prog="main.py",
        description=f"DD-Msg-Bot V{Config.VERSION} — DamaDam automation bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "mode", nargs="?",
        choices=["msg", "inbox", "activity"],
        help="Which mode to run (omit for interactive menu). 'activity' is an alias for 'inbox'.",
    )
    p.add_argument(
        "--max", dest="max_items", type=int, default=0, metavar="N",
        help="Maximum items to process (0 = unlimited)",
    )
    p.add_argument(
        "--debug", dest="debug", action="store_true",
        help="Enable verbose debug logging",
    )
    p.add_argument(
        "--headless", dest="headless", action="store_true", default=None,
        help="Force headless browser mode",
    )
    p.add_argument(
        "--stop-on-fail", dest="stop_on_fail", action="store_true",
        help="Stop the run immediately after the first Failed/RateLimited post",
    )
    p.add_argument(
        "--force-wait", dest="force_wait", type=int, metavar="SECONDS",
        help="Force wait N seconds before starting (useful to bypass cooldowns)",
    )
    return p


# ═══════════════════════════════════════════════════════════════════════════════
#  Interactive Local Menu
# ═══════════════════════════════════════════════════════════════════════════════

_MENU = """
╔══════════════════════════════════════════════════════════╗
║           DD-Msg-Bot V{ver}  —  DamaDam.pk Bot           ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║   1.  ✡  Message    Send messages to targets             ║
║   2.  ✡  Inbox      Sync inbox & send pending replies    ║
║   3.  ✡  Activity   Log DamaDam activity feed            ║
║                                                          ║
║   0.  Exit                                               ║
╚══════════════════════════════════════════════════════════╝
"""

def _interactive_menu() -> tuple:
    """
    Show the welcome menu in the terminal and return (mode, max_items, debug).
    Loops until the user makes a valid choice.
    """
    print(_MENU.format(ver=Config.VERSION))

    # Ask for max_items once (after mode selection)
    while True:
        raw = input("  Enter choice: ").strip()

        mode_map = {
            "1": "msg",
            "2": "inbox",
            "3": "activity",
            "0": None,
        }

        if raw not in mode_map:
            print("  ⚠  Invalid choice — enter 1–3 or 0 to exit.\n")
            continue

        mode = mode_map[raw]
        if mode is None:
            print("  Goodbye!\n")
            sys.exit(0)

        # For modes that support --max, ask for a limit
        max_items = 0
        if mode in ("msg", "inbox", "activity"):
            limit_raw = input(
                f"  Max items to process? (Enter for unlimited, 0=unlimited): "
            ).strip()
            if limit_raw.isdigit():
                max_items = int(limit_raw)

        return mode, max_items, False


# ═══════════════════════════════════════════════════════════════════════════════
#  Mode Runners
# ═══════════════════════════════════════════════════════════════════════════════

def _run_with_browser(mode: str, args) -> None:
    """
    Shared runner for modes that need a browser.
    Starts Chrome, logs in, connects to Sheets, runs the mode.
    """
    logger = Logger(mode)
    logger.section(f"DD-Msg-Bot V{Config.VERSION} — {mode.upper()} MODE")
    Config.validate()

    bm     = BrowserManager(logger)
    driver = bm.start()
    if not driver:
        logger.error("Browser failed to start — aborting")
        sys.exit(1)

    try:
        lm = LoginManager(driver, logger)
        if not lm.login():
            logger.error("Login failed — aborting")
            sys.exit(1)

        sheets = SheetsManager(logger)
        if not sheets.connect():
            logger.error("Google Sheets connection failed — aborting")
            sys.exit(1)

        max_n = getattr(args, "max_items", 0)

        if mode == "msg":
            message_mode.run(driver, sheets, logger, max_targets=max_n)
        elif mode == "inbox":
            inbox_mode.run_inbox(driver, sheets, logger)
        elif mode == "activity":  # backwards-compat alias
            inbox_mode.run_activity(driver, sheets, logger)

    finally:
        bm.close()




# ═══════════════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = _build_parser()
    args   = parser.parse_args()

    # Apply CLI overrides to Config
    if getattr(args, "debug", False):
        Config.DEBUG = True
    if getattr(args, "headless", None):
        Config.HEADLESS = True

    mode = args.mode

    # ── No mode given and NOT in CI → show interactive menu ──────────────────
    if not mode:
        if Config.IS_CI:
            parser.error("mode is required when running in CI / GitHub Actions")
        mode, max_n, debug = _interactive_menu()
        # Patch args so downstream functions see the menu choices
        args.max_items = max_n
        if debug:
            Config.DEBUG = True

    # ── Dispatch ─────────────────────────────────────────────────────────────
    if mode in ("msg", "inbox", "activity"):
        _run_with_browser(mode, args)
    else:
        parser.error(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
