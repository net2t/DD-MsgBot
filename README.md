# DD-Msg-Bot V4.1 — Unified Message Version

A streamlined Python bot for DamaDam.pk featuring unified message management: combines inbox and activity into one comprehensive system with date-organized logging and person record ID tracking.

---

## Features

- **Message Mode**: Send personalized messages to DamaDam users
- **Inbox Sync Mode**: Synchronize inbox and activity feed to Google Sheets
- **Google Sheets Integration**: Complete logging and queue management
- **React-compatible**: Properly handles DamaDam's React-powered text areas
- **Automated Scheduling**: GitHub Actions integration for regular runs

## Requirements

- Python 3.11+
- Google Chrome browser
- Google Cloud Service Account (for Sheets API)
- DamaDam.pk account credentials

## Setup

### 1. Clone and Install Dependencies
```bash
git clone https://github.com/net2t/DD-MsgBot.git
cd DD-MsgBot
pip install -r requirements.txt
```

### 2. Google Sheets Setup
1. Create a Google Cloud Service Account
2. Enable Google Sheets API
3. Download credentials JSON file
4. Create a new Google Sheet
5. Share the sheet with your service account email (Editor access)
6. Add your Sheet ID to `.env`

### 3. Environment Configuration
Copy `.env.sample` to `.env` and fill in your credentials:
```env
# DamaDam Credentials
DD_LOGIN_EMAIL=your_username
DD_LOGIN_PASS=your_password

# Google Sheets
DD_SHEET_ID=your_sheet_id_here
CREDENTIALS_FILE=credentials.json

# Browser Settings
DD_HEADLESS=1
DD_DISABLE_IMAGES=1

# Performance
DD_MSG_DELAY_SECONDS=3
DD_MAX_POST_PAGES=10
```

### 4. Initial Setup
Run the setup command to create all required sheets:
```bash
python main.py setup
```

## Usage

### Interactive Menu
```bash
python main.py
```

### Direct Commands
```bash
# Send messages (reads from MessageQueue sheet)
python main.py msg --max 50

# Sync inbox and activity (reads/writes MessageQueue sheet)
python main.py messages --max 100

# Create/refresh sheet structure
python main.py setup
```

### Options
- `--max N` - Process only N items (0 = unlimited)
- `--debug` - Enable verbose debug logging
- `--headless` - Force headless browser mode

## Sheet Structure

### Queue Sheets
- **MessageQueue**: Target users and message content
- **MsgQue**: Legacy message queue (backward compatible)

### Log Sheets
- **MessageLog**: Message sending history
- **MsgLog**: Legacy message log (backward compatible)
- **Logs**: Master activity log

### System Sheets
- **ScrapeState**: Pagination and state storage
- **Dashboard**: Analysis and metrics

## GitHub Actions

The bot includes automated workflows that:
- Run every 30 minutes
- Process up to 100 items per run
- Send messages automatically
- Upload logs on failure

## File Structure

```
DD-MsgBot/
├── main.py              # Entry point and CLI interface
├── config.py            # Configuration and constants
├── requirements.txt     # Python dependencies
├── .env.sample         # Environment template
├── core/               # Core functionality
│   ├── browser.py      # Chrome driver management
│   ├── login.py        # DamaDam authentication
│   └── sheets.py       # Google Sheets integration
├── modes/              # Bot operation modes
│   ├── message.py      # Message sending mode
│   ├── messages.py     # Inbox sync mode
│   └── setup.py        # Sheet setup mode
├── utils/              # Utilities
│   ├── helpers.py      # Helper functions
│   └── logger.py       # Logging system
└── .github/workflows/  # CI/CD automation
    └── bot.yml         # Scheduled runs
│   ├── messages.py          ← Unified Messages Mode (inbox + activity + replies)
│   ├── message.py           ← Legacy message sending (kept for compatibility)
│   └── setup.py             ← Sheet setup + formatting
├── utils/
│   ├── logger.py            ← Console + file logging (PKT timestamps)
│   └── helpers.py           ├── URL helpers, text sanitization
├── .github/
│   └── workflows/
│       └── bot.yml          ← Workflow for scheduled runs
└── logs/                    ← Auto-created log files (gitignored)
```

---

## Notes

- All timestamps are **Pakistan Standard Time (PKT, UTC+5)**
- Bot never overwrites read-only columns in MsgQue (TID, TYPE, LAST_MESSAGE)
- `damadam_cookies.pkl` stores session cookies for faster login — gitignored
- Log files are written to `logs/` — one file per mode per day
- Only two Google Sheets tabs are used: `MsgQue` and `MsgLog`
