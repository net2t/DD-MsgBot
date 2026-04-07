# DD-Msg-Bot V4.1 — Unified Message Version

A streamlined Python bot for DamaDam.pk featuring unified message management: combines inbox and activity into one comprehensive system with date-organized logging and person record ID tracking.

---

## Features

- **Message Mode**: Send personalized messages to users via nicknames or direct post URLs
- **Messages Mode**: Unified inbox + activity management with date-organized logging

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
| `mode` | One of: `msg messages setup` |
| `--max N` | Process only N items (default: 0 = unlimited) |
| `--debug` | Verbose debug output |
| `--headless` | Force headless browser (auto-enabled in CI) |

**Examples:**

```bash
python main.py msg --max 5          # Send to 5 targets only
python main.py messages             # Unified inbox + activity management
python main.py setup                # Create/initialize sheets
```

---

## GitHub Actions

A single workflow file (`.github/workflows/bot.yml`) handles all 5 scheduled runs:

| Mode | Schedule |
|------|----------|
| 🎀 Rekhta | Every 1 hour |
| 🎀 Message | Once a day (06:00 PKT) |
| 🎀 Post | Every 2 hours |
| 🎀 Inbox | Every 15 minutes |
| 🎀 Activity | Every 18 minutes |

**Manual run:** Go to **Actions → DD-Msg-Bot → Run workflow** and pick any mode from the dropdown.

### Required GitHub Secrets

| Secret | Description |
|--------|--------------|
| `DD_LOGIN_EMAIL` | DamaDam username (nick) |
| `DD_LOGIN_PASS` | DamaDam password |
| `DD_SHEET_ID` | Google Sheets ID |
| `GOOGLE_CREDENTIALS_JSON` | Full contents of `credentials.json` (paste the JSON) |
| `DD_LOGIN_EMAIL2` | *(optional)* Backup account username |
| `DD_LOGIN_PASS2` | *(optional)* Backup account password |
| `GEMINI_API_KEY` | *(optional)* For Urdu transliteration via Gemini API |

---

## Sheet Structure

### MsgQue

Targets for Message Mode.

| Column | Description |
|--------|--------------|
| MODE | Nick or URL |
| NAME | Display name (your reference) |
| NICK | DamaDam username or profile URL |
| CITY | Scraped city (read-only) |
| POSTS | Scraped post count (read-only) |
| FOLLOWERS | Scraped follower count (read-only) |
| GENDER | Scraped gender (read-only) |
| MESSAGE | Message text — supports `{{name}}`, `{{city}}` placeholders |
| STATUS | `Pending` → `Done` / `Skipped` / `Failed` |
| NOTES | Set by bot after each run |
| RESULT | URL of the post where message was sent |
| SENT_MSG | Actual resolved message that was sent |

### MessageQueue

Unified message queue (replaces InboxQue). Organized by person record ID.

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

### MessageLog

Unified message log (replaces InboxLog). Organized by date with complete history.

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

### Other Sheets

- **MsgLog**: History of all sent messages
- **PostQue**: Post content queue (if using post mode)
- **PostLog**: History of created posts
- **Logs**: Master activity log
- **ScrapeState**: Pagination cursors
- **Dashboard**: Summary/analysis (formulas only)

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
│   ├── message.py           ← Message Mode
│   ├── post.py              ← Post Mode (cooldown + duplicate detection)
│   ├── rekhta.py            ← Rekhta scraper
│   ├── inbox.py             ← Inbox + Activity modes
│   ├── logs.py              ← Log viewer
│   └── setup.py             ← Sheet setup + formatting
├── utils/
│   ├── logger.py            ← Console + file logging (PKT timestamps)
│   └── helpers.py           ← Image download, caption sanitization, URL helpers
├── .github/
│   └── workflows/
│       └── bot.yml          ← Single workflow: all 5 schedules + manual trigger
└── logs/                    ← Auto-created log files (gitignored)
```

---

## Post Mode Rules

- **Cooldown:** Minimum 135 seconds between posts (DamaDam rate limit)
- **Duplicate images:** If `IMG_LINK` was already posted → mark `Repeating`, skip, never retry
- **Rate limit hit:** Wait the required time → retry once only
- **Any other error:** Mark `Failed`, move on — never retry automatically

---

## Notes

- All timestamps are **Pakistan Standard Time (PKT, UTC+5)**
- Bot never overwrites the read-only reference columns in MsgList (CITY, POSTS, FOLLOWERS, GENDER)
- `damadam_cookies.pkl` stores session cookies for faster login — gitignored
- Log files are written to `logs/` — one file per mode per day
