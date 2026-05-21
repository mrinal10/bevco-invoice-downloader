"""
BEVCO Invoice Downloader
Run: C:\Python312\python.exe downloader.py
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

OUTPUT_DIR  = Path("Invoices")
INVOICE_URL = "https://excise.wb.gov.in/WBSBCL/Bevco/NIC/Page/CORP_Invoice.aspx"

MONTHS = [
    ("June",      "2025", "01/06/2025", "30/06/2025"),
    ("July",      "2025", "01/07/2025", "31/07/2025"),
    ("August",    "2025", "01/08/2025", "31/08/2025"),
    ("September", "2025", "01/09/2025", "30/09/2025"),
    ("October",   "2025", "01/10/2025", "31/10/2025"),
    ("November",  "2025", "01/11/2025", "30/11/2025"),
    ("December",  "2025", "01/12/2025", "31/12/2025"),
    ("January",   "2026", "01/01/2026", "31/01/2026"),
    ("February",  "2026", "01/02/2026", "28/02/2026"),
    ("March",     "2026", "01/03/2026", "31/03/2026"),
]

FROM_FIELD = "ctl00_ContentPlaceHolder1_TabContainer1_Tab_2_txtFrom"
TO_FIELD   = "ctl00_ContentPlaceHolder1_TabContainer1_Tab_2_txtTo"
SEARCH_BTN = "ctl00_ContentPlaceHolder1_TabContainer1_Tab_2_btnSrch"


def get_subfolder(indent_id):
    u = indent_id.upper()
    if "FLDR" in u: return "FL"
    if "CSDR" in u: return "CS"
    return None


def sanitize(name):
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()


def js_set_date(page, field_id, value):
    page.evaluate(f"""
        var el = document.getElementById('{field_id}');
        el.value = '{value}';
        ['change','input'].forEach(function(n){{
            var e = document.createEvent('HTMLEvents');
            e.initEvent(n,true,true);
            el.dispatchEvent(e);
        }});
    """)


def js_click(page, eid):
    page.evaluate(f"document.getElementById('{eid}').click()")


def get_rows(page):
    return page.evaluate("""
        (function(){
            var t=null;
            document.querySelectorAll('table').forEach(function(tb){
                var h=tb.rows[0]&&tb.rows[0].cells[0];
                if(h&&h.innerText.trim()==='Consignor Name') t=tb;
            });
            if(!t) return [];
            var out=[];
            for(var i=1;i<t.rows.length;i++){
                var r=t.rows[i],c=r.cells;
                if(c.length<5) continue;
                var indent=c[2]?c[2].innerText.trim():'';
                var inv=c[3]?c[3].innerText.trim():'';
                var a=r.querySelector('a[href*="doPostBack"]');
                if(!a) continue;
                var m=a.href.match(/doPostBack\\('([^']+)'/);
                if(indent&&m) out.push({indent_id:indent,invoice_no:inv,arg:m[1]});
            }
            return out;
        })()
    """)


def wait_for_table(page, timeout=30):
    for i in range(timeout):
        try:
            if page.evaluate("""
                (function(){
                    var f=false;
                    document.querySelectorAll('table').forEach(function(t){
                        var h=t.rows[0]&&t.rows[0].cells[0];
                        if(h&&h.innerText.trim()==='Consignor Name') f=true;
                    });
                    return f;
                })()
            """): return True
        except Exception:
            pass
        if i % 5 == 4:
            print(f"    [waiting for results table... {i+1}s]")
        time.sleep(1)
    return False


def download_one(page, row, dest_dir):
    indent = row["indent_id"].split("\n")[0].strip()
    inv    = sanitize(row["invoice_no"]) if row["invoice_no"] else sanitize(indent)
    arg    = row["arg"]
    sub    = get_subfolder(indent)
    if sub is None:
        print(f"      [SKIP] {indent}")
        return False

    out = dest_dir / sub
    out.mkdir(parents=True, exist_ok=True)
    pdf = out / f"{inv}.pdf"
    if pdf.exists():
        print(f"      [EXISTS] {sub}/{pdf.name}")
        return True

    print(f"      -> {sub}/{pdf.name}")
    try:
        with page.expect_download(timeout=20000) as dl:
            page.evaluate(f"__doPostBack('{arg}','')")
        dl.value.save_as(str(pdf))
        print(f"      [saved]")
        return True
    except Exception as e:
        print(f"      [ERROR] {e}")
        return False


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(accept_downloads=True, viewport=None)
        page    = context.new_page()

        page.goto(INVOICE_URL, wait_until="domcontentloaded")

        print("\n" + "="*60)
        print("  1. Log in (username, password, CAPTCHA -> Login)")
        print("  2. Click Invoice in the top menu")
        print("  3. Wait until you see the invoice TABLE on screen")
        print("  4. Come back here and press ENTER")
        print("="*60)
        input(">> Press ENTER when you can see the invoice table: ")

        try:
            page.screenshot(path="debug_screenshot.png", full_page=True)
        except Exception:
            pass

        log("Waiting for page to settle...")
        for i in range(15):
            try:
                page.wait_for_load_state("networkidle", timeout=3000)
                log(f"Page settled after {i+1}s")
                break
            except Exception:
                log(f"Still loading... ({i+1}s)")
            time.sleep(1)

        log(f"URL: {page.url}")

        if "CORP_Invoice" not in page.url:
            log("Navigating to invoice page...")
            try:
                page.goto(INVOICE_URL, wait_until="domcontentloaded", timeout=15000)
            except Exception:
                pass
            time.sleep(0.3)
            log(f"URL: {page.url}")

        has_form = page.evaluate(f"!!document.getElementById('{SEARCH_BTN}')")
        if not has_form:
            print("[ERROR] Form not found. Are you logged in?")
            input("Press ENTER to exit...")
            browser.close()
            return

        log("Starting downloads...\n")

        for month_name, year, from_date, to_date in MONTHS:
            folder = f"{month_name}-{year}"
            mdir   = OUTPUT_DIR / folder
            mdir.mkdir(parents=True, exist_ok=True)

            log(f"\n{'-'*60}")
            log(f"  {folder}  ({from_date} - {to_date})")
            log(f"{'-'*60}")
            input(f">> Set dates {from_date} to {to_date} in the browser, click Search, then press ENTER: ")

            log("  Searching...")
            if not wait_for_table(page, 30):
                log("  No results. Skipping.")
                continue

            body = page.inner_text("body")
            m = re.search(r"Total Record\(s\)\s*:\s*(\d+)", body)
            total = int(m.group(1)) if m else "?"
            log(f"  Records: {total}")
            if total == 0:
                log("  None found.")
                continue

            rows = get_rows(page)
            log(f"  {len(rows)} invoices to download")

            ok = skip = err = 0
            for i, row in enumerate(rows, 1):
                indent = row["indent_id"].split("\n")[0].strip()
                sub    = get_subfolder(indent)
                log(f"    [{i:>3}/{len(rows)}] {indent[:40]}  ->  {sub or 'UNKNOWN'}")
                if sub is None:
                    skip += 1; continue
                if download_one(page, row, mdir):
                    ok += 1
                else:
                    err += 1
                time.sleep(0.5)

            log(f"  Summary: {ok} saved, {skip} skipped, {err} errors")

        print("\n" + "="*60)
        print("ALL DONE!")
        print(f"Files in: {OUTPUT_DIR.resolve()}")
        print("="*60)
        input("Press ENTER to close browser...")
        browser.close()


if __name__ == "__main__":
    main()
