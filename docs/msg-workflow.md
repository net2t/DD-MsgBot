# Message Mode Workflow

This workflow handles sending messages to specified targets via DamaDam.pk.

## Steps to Run Message Mode

### 1. Prepare Your Targets
1. Open your Google Sheet
2. Go to the **MsgQue** sheet
3. Fill in the target information:
   - **MODE**: Enter "Nick" for username-based messaging or "URL" for direct post URL
   - **NAME**: Display name for your reference
   - **NICK**: DamaDam username or profile/post URL
   - **MESSAGE**: Your message text (supports {{name}} and {{city}} placeholders)
   - **STATUS**: Leave as "Pending" (bot will update this)

### 2. Run Message Mode

#### Interactive Mode:
```bash
python main.py
# Select option 1 for Message Mode
# Enter max items when prompted (or press Enter for unlimited)
```

#### Direct CLI:
```bash
python main.py msg [--max N] [--debug] [--headless]
```

**Examples:**
```bash
python main.py msg --max 5          # Send to 5 targets only
python main.py msg --debug          # Run with verbose logging
python main.py msg --headless       # Run without browser window
```

### 3. Monitor Progress
- Bot will show real-time progress in the terminal
- Each message attempt updates the **STATUS** column in MsgQue
- **RESULT** column will show the URL where message was sent
- **SENT_MSG** column shows the actual message that was sent
- All activity is logged to **MsgLog** sheet

### 4. Status Meanings
- **Pending**: Ready to send (default)
- **Done**: Message sent successfully
- **Failed**: Message failed to send
- **Skipped**: Target was skipped (e.g., already messaged)

### 5. Message Placeholders
Your message can use these placeholders:
- `{{name}}`: Will be replaced with the target's display name
- `{{city}}`: Will be replaced with the target's city (if available)

**Example Message:**
```
Hello {{name}}, I noticed you're from {{city}}. Great to connect!
```

### 6. Tips for Best Results

1. **Test Small First**: Use `--max 1` to test with a single target
2. **Check URLs**: For URL mode, ensure the post URL is accessible and allows messages
3. **Message Length**: Keep messages under 350 characters for best compatibility
4. **Rate Limits**: Bot includes automatic delays to respect DamaDam's rate limits
5. **Monitor Logs**: Check MsgLog sheet for detailed history of all sent messages

### 7. Troubleshooting

#### Common Issues:
- **Login Failed**: Check your DamaDam credentials in .env file
- **Sheet Not Found**: Run `python main.py setup` to create sheets
- **Messages Not Sending**: Check if target profiles allow messages
- **Rate Limited**: Wait longer between runs or reduce --max count

#### Debug Mode:
Add `--debug` flag to see detailed step-by-step execution:
```bash
python main.py msg --debug
```

### 8. Safety Features

- **Automatic Delays**: Built-in delays between messages to prevent rate limiting
- **Error Recovery**: Failed messages are marked but don't stop the entire run
- **Session Persistence**: Uses saved cookies to maintain login session
- **Dry Run Mode**: Set `DD_DRY_RUN=1` in .env to test without actually sending

---

**Need Help?**
- Check the logs in the terminal output for detailed error messages
- Review the MsgLog sheet for message history
- Ensure all required environment variables are set correctly
- Verify Google Sheets permissions are properly configured
