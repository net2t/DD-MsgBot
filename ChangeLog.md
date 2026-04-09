# Changelog

## [5.1.0]

### Major Changes

- **Inbox Reply Fixed**: Reply form TID-based matching on /inbox/ page
  - Bot `/inbox/` page pe form dhundta hai `input[name='tuid'][value='TID']` se
  - Sirf SEND button (dec=1) click karta hai, BLOCK/SKIP ignore
  - React-safe send_keys + native value setter fallback

- **Activity Parser Rewrite**: Proper HTML selectors used
  - MODE from `div.sp.cs.mrs span.ct`
  - NICK from `bdi` inside content span
  - POST text after nick
  - ACTION text "You replied to Nick on this post"
  - TID from remove button value last part "3:postid:tid"
  - Time from spans containing "ago"

- **Activity Pagination**: Proper page loop with ?page=N
  - Stops when no NEXT link found
  - Configurable max_pages (default 10)

- **Duplicate Check Improved**: Content-based (nick + message[:80])
  - More reliable than time-based de-dup
  - Covers both inbox and activity

- **2 Separate Workflows**:
  - `msg.yml` — Manual only (no schedule)
  - `inbox.yml` — Every 15 minutes + manual trigger

### Fixed

- Reply sending was using conv_url (post page) which has different form structure
- Now uses /inbox/ page where TID-based reply forms are always present
- Activity was not paginating correctly
- Activity duplicate check was unreliable

---

## [5.0.0]

### Major Changes

- **Reduced to 4 sheets**: MsgQue, MsgLog, Inbox, InboxLog
- **Inbox sheet**: One row per NICK (upsert, no duplicates)
- **Post selection**: Only picks posts with REPLIES button visible
- **0 Posts check**: Skip immediately with note
- **VLOOKUP columns**: D,E,F,G preserved, bot never writes to them
- **Clean menu**: 1=Msg, 2=Inbox, 3=Setup

---

## [4.1.0]

### Major Changes

- Unified Message System
- Date-Organized Logging
- Person Record ID (TID_NICK format)
- Streamlined Sheets

---

## [2.2.0]

### Major Changes

- Focused Version: 3 core modes (msg, inbox, activity)
- Removed: post, rekhta, logs, setup, format modes

---

## [2.0.0]

### Added

- Modular architecture
- Google Sheets retry system
- Logging with timestamps
