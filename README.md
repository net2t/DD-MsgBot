# DD-Msg-Bot V4.1 — Unified Message Version

A streamlined Python bot for DamaDam.pk featuring unified message management: combines inbox and activity into one comprehensive system with date-organized logging and person record ID tracking.

---

## Features

- **Messages Mode**: Unified inbox + activity management with date-organized logging and reply sending

---

## Key Improvements in V4.1

- **Unified Message System**: Merged inbox and activity into single comprehensive mode
- **Date-Organized Logging**: All messages organized by date for better tracking
- **Person Record ID**: Unique identifiers for each person (TID_NICK format)
- **Streamlined Sheets**: Reduced sheet count while maintaining full functionality
- **Enhanced Performance**: Optimized for faster execution and cleaner data organization
- **Simplified Interface**: Only 2 core modes for focused functionality

---

## Quick Start (Local)

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Sheets setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Sheets API** and **Google Drive API**
3. Create a **Service Account** → download key as `credentials.json`
4. Share your Google Sheet with the service account email (Editor access)

### 3. Create `.env`

```bash
cp .env.sample .env
# Fill in your values
```

Minimum required:

```env
DD_LOGIN_EMAIL=your_damadam_username
DD_LOGIN_PASS=your_password
DD_SHEET_ID=your_google_sheet_id
CREDENTIALS_FILE=credentials.json
```

### 4. Create sheets

```bash
python main.py setup
```

### 5. Run (interactive menu)

```bash
python main.py
```

Running with no arguments shows a numbered menu — no flags needed.

---

## CLI Usage (Direct / GitHub Actions)

```bash
python main.py <mode> [--max N] [--debug] [--headless]
```

| Argument | Description |
|----------|--------------|
| `mode` | One of: `messages setup` |
| `--max N` | Process only N items (default: 0 = unlimited) |
| `--debug` | Verbose debug output |
| `--headless` | Force headless browser (auto-enabled in CI) |

**Examples:**

```bash
python main.py messages             # Unified inbox + activity management + send replies
python main.py setup                # Create/initialize sheets
```

---

## Sheet Structure

### MsgQue

Unified message queue (inbox sync + pending replies). Organized by person record ID.

| Column | Description |
|--------|--------------|
| RECORD_ID | Unique ID (TID_NICK or NOID_NICK) |
| DATE | Date of conversation (YYYY-MM-DD) |
| NICK | DamaDam username |
| NAME | Display name |
| TYPE | 1ON1 / POST / MEHFIL / UNKNOWN |
| TID | DamaDam user ID |
| LAST_MESSAGE | Last message received |
| MY_REPLY | Your reply text — bot sends when STATUS=Pending |
| STATUS | Pending → Done / Failed / NoReply |
| UPDATED | Timestamp of last sync |
| NOTES | Set by bot |

### MsgLog

Unified message log (inbox events + activity + sent replies). Organized by date with complete history.

| Column | Description |
|--------|--------------|
| DATE | Date of message (YYYY-MM-DD) - for sorting |
| TIMESTAMP | PKT timestamp |
| RECORD_ID | Person record ID (TID_NICK or NOID_NICK) |
| NICK | Username |
| TYPE | 1ON1 / POST / MEHFIL / ACTIVITY |
| DIRECTION | IN / OUT / ACTIVITY |
| MESSAGE | Message text or activity description |
| CONV_URL | Link to conversation or post |
| STATUS | Received / Sent / Failed / Logged |

---

## File Structure

```
DD-Msg-Bot/
├── main.py                  ← Entry point + interactive menu
├── config.py                ← All settings (env vars + sheet/column definitions)
├── requirements.txt
├── .env                     ← Your credentials (gitignored)
├── .env.sample              ← Template — copy to .env
├── credentials.json         ← Google service account key (gitignored)
├── core/
│   ├── browser.py           ← Chrome setup
│   ├── login.py             ← Cookie → primary → backup login chain
│   └── sheets.py            ← All Google Sheets operations
├── modes/
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
