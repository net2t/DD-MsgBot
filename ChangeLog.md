 # Changelog

## [2.2.0]

### Major Changes

- **Focused Version**: Streamlined to 3 core modes only (msg, inbox, activity)
- **Removed Modes**: Eliminated post, rekhta, logs, setup, format modes
- **Separate Scope**: Inbox and Activity modes now have distinct purposes
  - Inbox Mode: Only sync conversations and send replies
  - Activity Mode: Only fetch and log activity feed

### Updated

- Enhanced message mode with dual input support (nicknames + direct post URLs)
- Optimized MAX_POST_PAGES default from 4 to 3 for faster processing
- Updated GitHub workflow to focus on 3 core modes
- Changed schedule from hourly posts to every 2 hours message processing
- Simplified interactive menu to show only 3 modes

### Fixed

- Fixed Unicode encoding issues in Windows terminal output
- Resolved activity mode timestamp field error
- Improved error handling for different input types

## [2.1.1]

### Updated

- Message mode: Enhanced to handle both nicknames and direct post URLs
- Nicknames: Search user profiles across multiple pages for open posts
- Post URLs: Direct processing without profile scanning
- Default MAX_POST_PAGES changed from 4 to 3 for faster processing
- Fixed Unicode encoding issues in Windows terminal output

### Fixed

- Sheet structure recreation to resolve MissingNick column errors
- Improved post URL detection and validation
- Enhanced error handling for different input types

## [2.0.1]

### Added

- Post mode: optional IMG_LINK population from POST_LINK
- Interactive menu when running without --mode

### Updated

- PostQueue parsing updated for TITLE_EN/TITLE_UR/IMG_LINK/POST_LINK layouts
- Post mode console output uses row references to avoid Urdu rendering issues

### Fixed

- Browser setup: fallback to Selenium Manager when local ChromeDriver fails/mismatches
- Post mode: prevent ChromeDriver non-BMP character crashes

## [2.0.0]

### Added
- Modular architecture
- Google Sheets retry system
- Logging with timestamps

### Updated
- Post mode: improved form detection on DamaDam share pages
- Post mode: improved post URL extraction after submit
- Post mode: image defaults set to Never expire + Turn Off Replies = Yes
- Repo hygiene: ignore chromedriver.exe; ensure .env/credentials.json are not committed

### Fixed
- Cookie handling
- Selenium stability

### Known Issues
- Headless detection possible

