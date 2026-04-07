# DD-Msg-Bot V4.1.0 - Cleanup Plan

## 📊 Active Sheets Structure (From Test Run)

### ✅ **KEEP - Currently Used:**
1. **MsgQue** - Message targets queue (used by msg mode)
2. **MessageQueue** - Unified message queue (used by messages mode) 
3. **MsgLog** - Message history (used by msg mode)
4. **MessageLog** - Unified message log (used by messages mode)
5. **Logs** - Master activity log (system)
6. **ScrapeState** - State storage (system)
7. **Dashboard** - Analysis sheet (user)

### ❌ **DELETE - Not Used:**
1. **PostQue** - Post content queue (no post mode)
2. **PostLog** - Post history (no post mode)

## 🗑️ Files & Code to Remove

### 1. Config.py Cleanup
**Remove these lines:**
- `SHEET_POST_QUE = "PostQue"`
- `SHEET_POST_LOG = "PostLog"`
- `POST_QUE_COLS` definition
- `POST_LOG_COLS` definition
- Post-related aliases

### 2. Setup.py Cleanup
**Remove from old sheet names:**
- `"PostQueue"` (already there)
- Update sheet count from 9 to 7

### 3. Remove Post-Related Code
**Files to check for post code:**
- Any remaining post references in core files
- Update ALL_SHEETS dictionary

## 📋 Minimal Structure After Cleanup

### Final Sheets (7 Total):
```
Queue Sheets (2):
├── MsgQue (Message targets)
└── MessageQueue (Unified inbox)

Log Sheets (2):
├── MsgLog (Message history)  
└── MessageLog (Unified log)

System Sheets (3):
├── Logs (Master log)
├── ScrapeState (State storage)
└── Dashboard (Analysis)
```

### Final Modes (2):
```
1. 📤 Send Messages (msg)
   - Reads from MsgQue
   - Writes to MsgLog

2. 📥 Inbox Activity (messages)  
   - Reads/writes MessageQueue
   - Writes to MessageLog
```

## 🔧 Cleanup Actions

1. Update config.py to remove post sheets
2. Update setup.py to reflect 7 sheets
3. Update documentation
4. Test both modes still work
5. Commit changes

This will simplify the codebase while keeping all functionality you actually use.
