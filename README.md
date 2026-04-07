# DD-Msg-Bot V2 — Focused Version (3 Core Modes)

A streamlined Python bot for DamaDam.pk focused on essential automation tasks: messaging, inbox management, and activity monitoring.

---

## Features

- **Message Mode**: Send personalized messages to users via nicknames or direct post URLs
- **Inbox Mode**: Sync inbox conversations and send pending replies
- **Activity Mode**: Monitor and log DamaDam activity feed

---

## Key Improvements in Focused Version

- **Streamlined Interface**: Only 3 core modes for focused functionality
- **Enhanced Message Processing**: Dual input support (nicknames + direct post URLs)
- **Separate Scope**: Inbox and Activity modes now have distinct purposes
- **Optimized Performance**: Reduced complexity and faster execution
- **Cleaner Codebase**: Removed unused modes and dependencies

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
| `mode` | One of: `rekhta msg post inbox activity logs setup format` |
| `--max N` | Process only N items (default: 0 = unlimited) |
| `--debug` | Verbose debug output |
| `--headless` | Force headless browser (auto-enabled in CI) |

**Examples:**

```bash
python main.py msg --max 5          # Send to 5 targets only
python main.py post --max 1         # Post 1 item (safe test)
python main.py rekhta --max 30      # Scrape up to 30 new cards
python main.py inbox                # Sync inbox + send replies
python main.py format               # Apply sheet formatting
python main.py logs                 # View recent activity
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

### MsgList

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

### PostQueue

Queue for Post Mode. Populated by Rekhta Mode.

| Column | Description |
|--------|--------------|
| STATUS | `Pending` → `Done` / `Failed` / `Repeating` |
| TYPE | `image` or `text` |
| TITLE | Roman Urdu first line (reference) |
| URDU | Urdu caption — use `=GOOGLETRANSLATE(...)` formula |
| IMG_LINK | Full image URL from Rekhta |
| POET | Poet name |
| POST_URL | Filled by bot after successful post |
| ADDED | Timestamp when row was scraped |
| NOTES | Error details set by bot |

### InboxQueue

Inbox reply queue for Inbox Mode.

| Column | Description |
|--------|--------------|
| NICK | DamaDam username |
| NAME | Display name |
| LAST_MSG | Last message received |
| MY_REPLY | Your reply text — bot sends this when STATUS=Pending |
| STATUS | `Pending` → `Done` / `Failed` |
| TIMESTAMP | When conversation was first synced |
| NOTES | Set by bot |

### MasterLog

All bot activity is logged here automatically.

| Column | Description |
|--------|--------------|
| TIMESTAMP | PKT timestamp |
| MODE | Which mode ran |
| ACTION | What action was performed |
| NICK | Target username |
| URL | Relevant URL |
| STATUS | Result status |
| DETAILS | Extra detail / error message |

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
