@echo off
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Installing Playwright browser...
playwright install chromium
echo.
echo Setup complete! Run the downloader with:
echo   python downloader.py
pause
