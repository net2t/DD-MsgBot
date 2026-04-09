# DD-Msg-Bot V5.1 — DamaDam.pk Automation

Streamlined Python bot for DamaDam.pk with 2 core modes and 4 Google Sheets.

---

## Modes

| Mode | Kaam |
|------|------|
| **msg** | MsgQue sheet se targets padhta hai, post pe reply bhejta hai |
| **inbox** | Inbox sync karta hai + activity log karta hai + pending replies bhejta hai |
| **setup** | 4 sheets create/recreate karta hai (fresh start) |

---

## Quick Start (Local)

### 1. Dependencies install karo
```bash
pip install -r requirements.txt
```

### 2. `.env` file banao
```bash
cp .env.sample .env
# Fill in your values
```

Minimum required:
```env
DD_LOGIN_EMAIL=your_damadam_nick
DD_LOGIN_PASS=your_password
DD_SHEET_ID=your_google_sheet_id
CREDENTIALS_FILE=credentials.json
```

### 3. Google Sheets setup
1. [Google Cloud Console](https://console.cloud.google.com/) mein project banao
2. **Google Sheets API** + **Google Drive API** enable karo
3. **Service Account** banao → key download karo as `credentials.json`
4. Apni Google Sheet service account email ke saath share karo (Editor access)

### 4. Sheets create karo
```bash
python main.py setup
```

### 5. Run karo (interactive menu)
```bash
python main.py
```

---

## Menu
```
  ╔══════════════════════════════════════════════╗
  ║      DD-Msg-Bot V5.1  —  DamaDam.pk         ║
  ╠══════════════════════════════════════════════╣
  ║                                              ║
  ║   1.  Send Messages  (MsgQue targets)        ║
  ║   2.  Inbox Sync     (Inbox + Activity)      ║
  ║   3.  Setup Sheets   (Create / Recreate)     ║
  ║                                              ║
  ║   0.  Exit                                   ║
  ╚══════════════════════════════════════════════╝
```

---

## CLI Usage
```bash
python main.py msg             # Message mode (unlimited)
python main.py msg --max 5     # Send to max 5 targets only
python main.py inbox           # Inbox sync + activity + replies
python main.py setup           # Create/recreate sheets
python main.py msg --debug     # Verbose logging
```

---

## Sheet Structure (4 sheets)

### 1. MsgQue — Outbound message targets
Aap fill karo, bot bhejta hai.

| Col | Name | Description |
|-----|------|-------------|
| A | MODE | Nick ya URL |
| B | NAME | Display name (aapka reference) |
| C | NICK | DamaDam username ya profile URL |
| D | CITY | **VLOOKUP formula** (bot kabhi nahi likhta) |
| E | POSTS | **VLOOKUP formula** (bot kabhi nahi likhta) |
| F | FOLLOWERS | **VLOOKUP formula** (bot kabhi nahi likhta) |
| G | GENDER | **VLOOKUP formula** (bot kabhi nahi likhta) |
| H | MESSAGE | Message template (`{{name}}`, `{{city}}` etc.) |
| I | STATUS | `Pending` → `Done` / `Skipped` / `Failed` |
| J | NOTES | Bot likhta hai reason + timestamp |
| K | RESULT | Post URL jahan message bheja |
| L | SENT_MSG | Actual resolved message text |

**VLOOKUP formulas (D, E, F, G columns — row 3 se shuru karo):**
```
D3 (CITY):      =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),3,FALSE),"")
E3 (POSTS):     =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),6,FALSE),"")
F3 (FOLLOWERS): =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),8,FALSE),"")
G3 (GENDER):    =IFERROR(VLOOKUP(C3,IMPORTRANGE("SHEET_ID","Profiles!B:K"),4,FALSE),"")
```

**STATUS values:**
- `Pending` — bot process karega
- `Done` — message sent successfully
- `Skipped` — 0 Posts / Must Follow First / Replies Off
- `Failed` — unexpected error

**Message templates:**
```
Aoa {{name}} ji, kya haal hai?
Aoa {{name}} ({{city}}), mashAllah {{posts}} posts hain!
```

### 2. MsgLog — Sent message history
Bot automatically fill karta hai.

| Col | Name | Description |
|-----|------|-------------|
| A | DATE | YYYY-MM-DD |
| B | TIMESTAMP | PKT timestamp |
| C | NICK | Target username |
| D | NAME | Display name |
| E | POST_URL | Post URL |
| F | STATUS | Sent / Failed / Skipped |
| G | NOTES | Reason |
| H | MESSAGE | Actual message sent |

### 3. Inbox — Inbox sync queue
**One row per NICK — no duplicates.** Bot upsert karta hai (update existing ya add new).

| Col | Name | Description |
|-----|------|-------------|
| A | NICK | DamaDam username (unique key) |
| B | TID | DamaDam internal user ID |
| C | TYPE | 1ON1 / POST / MEHFIL |
| D | LAST_MSG | Last message received |
| E | DATE | Date of last message |
| F | TIME_STR | "2 hours ago" etc. |
| G | MY_REPLY | **Aap yahan reply likhein** |
| H | STATUS | New / Pending / Done / Failed |
| I | CONV_URL | Conversation link |
| J | UPDATED | Last sync timestamp |
| K | NOTES | Bot notes |

**Reply bhejne ka flow:**
1. Bot sync karta hai → STATUS = `New`
2. Aap `MY_REPLY` column mein reply likho → STATUS = `Pending`
3. Agli baar inbox mode chalega → reply bhejega → STATUS = `Done`

### 4. InboxLog — Complete history
Append-only. Har inbox event + har activity item yahan record hota hai.

| Col | Name | Description |
|-----|------|-------------|
| A | DATE | YYYY-MM-DD (sorting ke liye) |
| B | TIMESTAMP | PKT timestamp |
| C | NICK | Username |
| D | TID | User ID |
| E | TYPE | 1ON1 / POST / MEHFIL / ACTIVITY |
| F | DIRECTION | IN / OUT / ACTIVITY |
| G | MESSAGE | Message ya activity text |
| H | CONV_URL | Conversation ya post link |
| I | STATUS | Received / Sent / Failed / Logged |

---

## Message Mode — Post Selection Logic

Bot sirf woh posts pick karta hai jis pe **REPLIES button** visible ho:
- Profile page pe `a[itemprop='discussionUrl']` dhundta hai
- Ye element sirf tab render hota hai jab replies on hain
- Post count 0 ho → immediately skip (`0 Posts`)
- Post pe `REPLIES OFF` → `Skipped` with note "Replies Off"
- `FOLLOW TO REPLY` → `Skipped` with note "Must Follow First"

---

## Inbox Mode — How it works

**Phase 1 — Inbox sync:**
- `/inbox/` page se sab conversations parse karta hai
- Har NICK ke liye ek row (no duplicates)
- Existing NICK → row update, new NICK → row add
- InboxLog mein har message append (content-based de-dup)

**Phase 2 — Activity feed:**
- `/inbox/activity/` ke sab pages (pagination support)
- NEXT button tak chalata rehta hai
- Har activity item: MODE | NICK | POST text | Action | Time
- InboxLog mein append (content-based de-dup)

**Phase 3 — Send replies:**
- Inbox sheet se `STATUS=Pending` + `MY_REPLY` filled rows dhundta hai
- `/inbox/` page pe reply form find karta hai by TID
- SEND button (dec=1) click karta hai
- `STATUS=Done` ya `Failed` mark karta hai

---

## GitHub Actions (2 Workflows)

### msg.yml — Manual only
```
Actions → Send Messages → Run workflow
```
- `max_items`: Kitne messages bhejne hain (0 = unlimited)
- `debug`: Debug logging on/off

### inbox.yml — Auto (every 15 min) + Manual
- Automatically har 15 minute mein chalta hai
- Manual trigger bhi available

### Required Secrets
| Secret | Description |
|--------|-------------|
| `DD_LOGIN_EMAIL` | DamaDam username |
| `DD_LOGIN_PASS` | DamaDam password |
| `DD_SHEET_ID` | Google Sheets ID |
| `GOOGLE_CREDENTIALS_JSON` | credentials.json ka poora content |
| `DD_LOGIN_EMAIL2` | (optional) Backup account |
| `DD_LOGIN_PASS2` | (optional) Backup password |

---

## File Structure
```
DD-Msg-Bot/
├── main.py              ← Entry point + interactive menu
├── config.py            ← All settings + sheet/column definitions
├── requirements.txt     ← Python dependencies
├── .env                 ← Your credentials (gitignored)
├── .env.sample          ← Template
├── credentials.json     ← Google service account key (gitignored)
├── core/
│   ├── browser.py       ← Chrome setup + cookie handling
│   ├── login.py         ← Login: cookie → primary → backup
│   └── sheets.py        ← Google Sheets read/write operations
├── modes/
│   ├── message.py       ← Message Mode (send to profile posts)
│   ├── inbox.py         ← Inbox Mode (sync + activity + replies)
│   └── setup.py         ← Sheet creation + formatting
├── utils/
│   ├── logger.py        ← Console + file logging (PKT timestamps)
│   └── helpers.py       ← URL helpers, text sanitization
├── .github/
│   └── workflows/
│       ├── msg.yml      ← Message workflow (manual only)
│       └── inbox.yml    ← Inbox workflow (every 15 min + manual)
└── logs/                ← Auto-created log files (gitignored)
```

---

## Notes
- Sab timestamps **Pakistan Standard Time (PKT, UTC+5)**
- VLOOKUP cols (D, E, F, G) mein bot kabhi nahi likhta — aap manually formulas daalo
- `damadam_cookies.pkl` — session cookies store, gitignored
- Logs: `logs/` folder mein, ek file per mode per day
