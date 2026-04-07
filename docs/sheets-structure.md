# DD-Msg-Bot V4.1.0 - Sheets Structure

## Overview
The setup creates **9 sheets** total with the following organization:

## 📊 Sheet List

### Queue Sheets (3)
1. **MsgQue** - Message targets queue
2. **PostQue** - Post content queue (if using post mode)
3. **MessageQueue** - Unified message queue (replaces InboxQue)

### Log Sheets (3)
4. **MsgLog** - History of sent messages
5. **PostLog** - History of created posts
6. **MessageLog** - Unified message log (replaces InboxLog)

### System Sheets (2)
7. **Logs** - Master activity log
8. **ScrapeState** - Pagination cursors and state

### Dashboard (1)
9. **Dashboard** - Summary/analysis (formula-based, empty)

---

## 📋 Column Headings

### 1. MsgQue (Message Targets)
| Column | Header | Description |
|--------|--------|-------------|
| A | MODE | Nick or URL |
| B | NAME | Display name (your reference) |
| C | NICK | DamaDam username or profile URL |
| D | CITY | Scraped city (read-only) |
| E | POSTS | Scraped post count (read-only) |
| F | FOLLOWERS | Scraped follower count (read-only) |
| G | GENDER | Scraped gender (read-only) |
| H | MESSAGE | Message text — supports {{name}}, {{city}} |
| I | STATUS | Pending → Done / Skipped / Failed |
| J | NOTES | Set by bot |
| K | RESULT | URL of post where message was sent |
| L | SENT_MSG | Actual resolved message that was sent |

### 2. MessageQueue (Unified Message Queue)
| Column | Header | Description |
|--------|--------|-------------|
| A | RECORD_ID | Unique ID (TID_NICK or NOID_NICK) |
| B | DATE | Date of conversation (YYYY-MM-DD) |
| C | NICK | DamaDam username |
| D | NAME | Display name |
| E | TYPE | 1ON1 / POST / MEHFIL / UNKNOWN |
| F | TID | DamaDam user ID |
| G | LAST_MESSAGE | Last message received |
| H | MY_REPLY | Your reply text — bot sends when STATUS=Pending |
| I | STATUS | Pending → Done / Failed / NoReply |
| J | UPDATED | Timestamp of last sync |
| K | NOTES | Set by bot |

### 3. MessageLog (Unified Message Log)
| Column | Header | Description |
|--------|--------|-------------|
| A | DATE | Date of message (YYYY-MM-DD) - for sorting |
| B | TIMESTAMP | PKT timestamp |
| C | RECORD_ID | Person record ID (TID_NICK or NOID_NICK) |
| D | NICK | Username |
| E | TYPE | 1ON1 / POST / MEHFIL / ACTIVITY |
| F | DIRECTION | IN / OUT / ACTIVITY |
| G | MESSAGE | Message text or activity description |
| H | CONV_URL | Link to conversation or post |
| I | STATUS | Received / Sent / Failed / Logged |

### 4. MsgLog (Message History)
| Column | Header | Description |
|--------|--------|-------------|
| A | TIMESTAMP | PKT timestamp |
| B | NICK | Target username |
| C | NAME | Display name |
| D | MESSAGE | Message text that was sent |
| E | POST_URL | URL of post where message was sent |
| F | STATUS | Sent / Failed / Skipped |
| G | NOTES | Error or extra detail |

### 5. PostQue (Post Queue)
| Column | Header | Description |
|--------|--------|-------------|
| A | STATUS | Pending → Done / Failed / Repeating |
| B | TYPE | image / text |
| C | TITLE | Roman Urdu first line (reference) |
| D | URDU | Urdu caption — use =GOOGLETRANSLATE() formula |
| E | IMG_LINK | Full image URL from Rekhta |
| F | POET | Poet name |
| G | POST_URL | Filled by bot after successful post |
| H | ADDED | Timestamp when row was scraped |
| I | NOTES | Error details set by bot |

### 6. PostLog (Post History)
| Column | Header | Description |
|--------|--------|-------------|
| A | TIMESTAMP | PKT timestamp |
| B | TYPE | image / text |
| C | POET | Poet name |
| D | TITLE | Roman Urdu first line |
| E | POST_URL | URL of the created post |
| F | IMG_LINK | Source image URL |
| G | STATUS | Posted / Failed / Repeating / Skipped |
| H | NOTES | Error or extra detail |

### 7. Logs (Master Activity Log)
| Column | Header | Description |
|--------|--------|-------------|
| A | TIMESTAMP | PKT timestamp |
| B | MODE | Which mode ran |
| C | ACTION | What action was performed |
| D | NICK | Target username |
| E | URL | Relevant URL |
| F | STATUS | Result status |
| G | DETAILS | Extra detail / error message |

### 8. ScrapeState (State Storage)
| Column | Header | Description |
|--------|--------|-------------|
| A | KEY | State key (e.g. "rekhta_last_page") |
| B | VALUE | State value |
| C | UPDATED | When this value was last written |

### 9. Dashboard (Analysis)
- **Empty sheet** - Add your own formulas and analysis
- No fixed columns - completely user-managed

---

## 🔄 Setup Process

1. Run `python main.py setup` to create all sheets
2. Old sheets will be automatically deleted
3. New sheets will be created with proper headers
4. Dashboard sheet will be created empty

## 📝 Usage Notes

- **MessageQueue** and **MessageLog** are the new unified sheets (V4.1.0)
- **InboxQue** and **InboxLog** are replaced but still work as aliases
- **RunLog** has been removed - functionality moved to **Logs** sheet
- All sheets are created with proper formatting and frozen headers
- Dashboard is ready for your custom formulas and charts
