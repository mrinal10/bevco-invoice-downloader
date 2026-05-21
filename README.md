# BEVCO Invoice Downloader

Automates downloading of invoices from the West Bengal State Beverages Corporation (WBSBCL) .

---

## Requirements

- Python 3.12 — installed at `C:\Python312\python.exe`
- Packages: `playwright>=1.40.0`

### First-time setup

Run `setup.bat` once to install dependencies and the Playwright browser:

```
setup.bat
```

Or manually:

```
C:\Python312\python.exe -m pip install playwright
C:\Python312\python.exe -m playwright install chromium
```

---

## How to Run

```
C:\Python312\python.exe downloader.py
```

---

## What It Does — Step by Step

### 1. Browser opens
A visible Chromium browser window opens and navigates to the WBSBCL invoice portal login page.

### 2. You log in manually
The script pauses and prints instructions. In the browser:
- Enter your **username** and **password**
- Type the **CAPTCHA** code shown in the image
- Click **Login**
- Click **Invoice** in the top navigation menu
- Wait until the invoice search table appears on screen

Then press **ENTER** in the terminal.

### 3. Month-by-month downloads
For each month in the `MONTHS` list, the script:
1. Prints the expected date range (e.g. `01/06/2025 to 30/06/2025`)
2. **Pauses** — you manually set the From/To dates in the browser and click **Search**
3. You press **ENTER** in the terminal once results are visible
4. The script reads all invoice rows from the results table
5. Each invoice is downloaded via the portal's postback mechanism and saved as a PDF

### 4. Done
When all months are processed, the script prints `ALL DONE!` and waits for you to press ENTER before closing the browser.

---

## Output Folder Structure

```
Invoices/
  June-2025/
    FL/          <- Foreign Liquor (Indent IDs containing "FLDR")
    CS/          <- Country Spirit (Indent IDs containing "CSDR")
  July-2025/
    FL/
    CS/
  ...
  March-2026/
    FL/
    CS/
```

Each PDF is named after the **Invoice Number** from the portal.

---

## Months Configured

Edit the `MONTHS` list in `downloader.py` to change the range. Each entry is:

```python
("MonthName", "YYYY", "DD/MM/YYYY", "DD/MM/YYYY")
#              year    from-date      to-date
```

Current configuration runs **June 2025 → March 2026**.

---

## Portal Details

| Item | Value |
|---|---|
| Portal URL | https://excise.wb.gov.in/WBSBCL/Bevco/NIC/ |
| Login page | `.../UserLogin/Login.aspx` |
| Invoice page | `.../Page/CORP_Invoice.aspx` |

---

## Key Behaviour Notes

- **Already-downloaded files are skipped** — safe to re-run if interrupted. The script checks if the PDF already exists before downloading.
- **CAPTCHA is manual** — the portal uses an image-based numeric CAPTCHA that must be typed by the user.
- **Downloads are triggered via `__doPostBack`** — the portal uses ASP.NET Web Forms postbacks to serve PDFs. The script intercepts the browser's download event to capture and save the file.
- **Subfolder is determined by Indent ID** — `tFLDR/...` goes to `FL/`, `tCSDR/...` goes to `CS/`. Rows with neither are skipped.
- **Session expiry** — if the session expires mid-run, the browser will redirect to the login page. Close and restart the script.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `Form not found` error at startup | You are not logged in or not on the invoice page. Follow the login steps and press ENTER only after the table is visible. |
| Invoice download times out | The portal may be slow. The timeout is 20 seconds per invoice. Re-run — already-saved files will be skipped. |
| PDF saved as 0 bytes or wrong file | The session may have expired. Restart and log in again. |
| Browser closes unexpectedly | A Python error occurred. Check the terminal output for `[ERROR]` messages. |

---

## Files

| File | Purpose |
|---|---|
| `downloader.py` | Main script |
| `requirements.txt` | Python dependencies |
| `setup.bat` | One-time install script |
| `debug_screenshot.png` | Screenshot taken at startup (auto-generated, useful for debugging) |
| `Invoices/` | Output folder (auto-created) |
