@echo off
echo DD-Msg-Bot V5.1 - Sync ^& Push
echo ================================
echo.
git add .
git commit -m "DD-Msg-Bot V5.1 - Inbox + Activity fix, 2 workflows"
git push
echo.
echo Done! Pushed to GitHub.
pause
