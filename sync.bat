@echo off
echo DD-Msg-Bot V4.1.0 - Sync & Push Script
echo =====================================

echo.
echo Adding all changes to git...
git add .

echo.
echo Committing changes...
git commit -m "Update DD-Msg-Bot V4.1.0 - Unified Message System"

echo.
echo Pushing to remote repository...
git push

echo.
echo Sync complete! Your changes are now pushed to GitHub.
echo.
pause
