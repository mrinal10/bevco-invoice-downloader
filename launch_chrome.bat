@echo off
echo Closing existing Chrome instances...
taskkill /F /IM chrome.exe /T >nul 2>&1
timeout /t 2 >nul

echo Launching Chrome with remote debugging on port 9222...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_bevco"

echo.
echo Chrome is starting with remote debugging enabled.
echo Now log in to the BEVCO portal, navigate to the Invoice page,
echo then run:  C:\Python312\python.exe downloader.py
echo.
pause
