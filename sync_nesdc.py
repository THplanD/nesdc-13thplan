"""Download original NESDC CSV exports for all 13 milestones.

Closes the site's promotional report dialog before clicking the existing CSV
button. Saves original download bytes without rebuilding the dataset.
"""
import asyncio
import csv
import io
import os
from pathlib import Path
from playwright.async_api import async_playwright

SOURCE = 'https://13thplan-nesdc.vercel.app/'
ROOT = Path(__file__).parent
DEST = ROOT / 'csv'
DEBUG = ROOT / 'debug'
DEST.mkdir(exist_ok=True)


def validate_csv(data: bytes, milestone: int) -> int:
    rows = csv.DictReader(io.StringIO(data.decode('utf-8-sig')))
    columns = rows.fieldnames or []
    if not {'milestoneKey', 'indicatorId'}.issubset(columns):
        raise ValueError(f'Unexpected CSV columns: {columns[:8]}')
    items = list(rows)
    if not items:
        raise ValueError('Empty CSV')
    if any(row['milestoneKey'].strip() != f'milestone{milestone}' for row in items):
        raise ValueError(f'CSV data does not belong to milestone {milestone}')
    return len(items)


async def close_promo_popup(page):
    """Dismiss optional on-load NESDC report banner without assuming its ID.

    The overlay can be created after DOMContentLoaded. Restrict selectors to
    visible dialogs / overlay-style containers and prefer their close buttons.
    If a version of the site has no banner, this is a no-op.
    """
    await page.wait_for_timeout(900)
    candidate_selectors = [
        '#modal-container button[aria-label*="ปิด"]',
        '#modal-container button[title*="ปิด"]',
        '[role="dialog"] button[aria-label*="ปิด"]',
        '[role="dialog"] button[aria-label="Close"]',
        '[aria-modal="true"] button[aria-label*="close" i]',
        'button[aria-label="ปิดหน้าต่าง"]',
        'button[title="Close"]',
    ]
    for selector in candidate_selectors:
        buttons = page.locator(selector)
        for i in range(min(await buttons.count(), 5)):
            btn = buttons.nth(i)
            if await btn.is_visible():
                try:
                    await btn.click(timeout=1500)
                    print(f'Closed promo overlay via {selector}')
                    return
                except Exception:
                    continue

    # Fallback: discover the overlay containing the characteristic report
    # announcement, then press its top-right close button. Only act when the
    # report promo is actually visible; do not remove unrelated site dialogs.
    result = await page.evaluate('''() => {
      const text = 'รายงานผลการพัฒนาเศรษฐกิจและสังคมของประเทศ 3 ปี';
      const inView = e => { const r=e.getBoundingClientRect(); const s=getComputedStyle(e);
        return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
      const nodes=[...document.querySelectorAll('div,section,[role="dialog"]')].filter(e=>
        inView(e) && (e.innerText||'').includes(text) && e.getBoundingClientRect().width>400);
      nodes.sort((a,b)=>a.getBoundingClientRect().width-b.getBoundingClientRect().width);
      for (const n of nodes) {
        const buttons=[...n.querySelectorAll('button')].filter(inView);
        if (!buttons.length) continue;
        const r=n.getBoundingClientRect();
        const candidates=buttons.filter(b=>{const x=b.getBoundingClientRect();
          return x.top<r.top+100 && x.right>r.right-110; });
        const b=candidates[0];
        if (b) {b.click(); return 'clicked close button';}
      }
      return 'popup not detected';
    }''')
    print(f'Promo check: {result}')


async def download_one(page, number: int):
    await page.goto(f'{SOURCE}?milestone={number}', wait_until='domcontentloaded', timeout=60000)
    await close_promo_popup(page)
    button = page.locator(f'button.csv-icon-btn[aria-label="ดาวน์โหลด CSV หมุดหมายที่ {number}"]').first
    await button.wait_for(state='attached', timeout=90000)
    await button.scroll_into_view_if_needed(timeout=15000)
    try:
        async with page.expect_download(timeout=45000) as dl:
            await button.click(timeout=12000)
    except Exception as first_error:
        # The banner may have been displayed late or has a different close
        # element. Dispatch the same click from page JS, bypassing an overlay.
        print(f'Normal click blocked; trying element click: {type(first_error).__name__}')
        await close_promo_popup(page)
        async with page.expect_download(timeout=45000) as dl:
            await button.evaluate('(el) => el.click()')
    download = await dl.value
    problem = await download.failure()
    if problem:
        raise RuntimeError(f'Download failed: {problem}')
    tmp = DEST / f'.milestone-{number}.tmp'
    await download.save_as(tmp)
    data = tmp.read_bytes()
    count = validate_csv(data, number)
    output = DEST / f'dashboard-data-milestone-{number}.csv'
    tmp.replace(output)
    return count, len(data), download.suggested_filename


async def main():
    start = int(os.getenv('MIN_MILESTONE', '1'))
    end = int(os.getenv('MAX_MILESTONE', '13'))
    failures, successes = [], []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(
            accept_downloads=True, locale='th-TH', viewport={'width':1440,'height':900})
        page = await context.new_page()
        for num in range(start, end + 1):
            for attempt in range(1, 4):
                try:
                    count, size, filename = await download_one(page, num)
                    print(f'OK #{num}: {count} records / {size} bytes / {filename}')
                    successes.append(num)
                    break
                except Exception as exc:
                    print(f'FAILED #{num}, attempt {attempt}/3: {type(exc).__name__}: {str(exc)[:450]}')
                    if attempt == 3:
                        failures.append(num)
                        DEBUG.mkdir(exist_ok=True)
                        try:
                            await page.screenshot(path=str(DEBUG / f'milestone-{num}.png'), full_page=False, timeout=10000)
                        except Exception:
                            pass
                    else:
                        await asyncio.sleep(2*attempt)
        await browser.close()
    print(f'Updated: {successes}; failed: {failures}; existing CSV files preserved')
    if failures:
        raise SystemExit(1)

if __name__ == '__main__':
    asyncio.run(main())
