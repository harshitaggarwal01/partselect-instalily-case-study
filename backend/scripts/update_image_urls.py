"""One-time script: fetch correct image URLs for all products in products.json.

PartSelect requires real browser rendering — httpx is blocked.
This script uses Playwright to load each part page in a real browser.

Setup:
    pip install playwright
    playwright install chromium

Usage:
    cd backend
    python scripts/update_image_urls.py [--headless]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

DATA_PATH = Path(__file__).parent.parent / "app" / "data" / "products.json"
PS_BASE = "https://www.partselect.com"


def fetch_image_url_playwright(page, product: dict) -> tuple[str | None, str | None]:
    """Load the product page and extract the image URL + canonical page URL.

    Returns (image_url, canonical_url) — either may be None on failure.
    """
    part_number = product.get("part_number", "")
    # PS-prefixed numbers redirect correctly; for others try search
    if part_number.upper().startswith("PS"):
        try_url = f"{PS_BASE}/{part_number.upper()}.htm"
    else:
        # Use search URL — PartSelect redirects to the part page if unique match
        try_url = f"{PS_BASE}/search.aspx?SearchTerm={part_number}"

    try:
        page.goto(try_url, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_selector('img[itemprop="image"]', timeout=8000)
        img_src = page.eval_on_selector('img[itemprop="image"]', "el => el.src")
        canonical = page.url
        return img_src, canonical
    except Exception:
        return None, None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true", help="Run browser headlessly")
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && playwright install chromium")
        raise SystemExit(1)

    products = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    updated = 0

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=args.headless)
        page = browser.new_page()
        page.set_extra_http_headers({"Accept-Language": "en-US,en;q=0.9"})

        for product in products:
            pn = product.get("part_number", "")
            old_url = product.get("image_url", "") or ""

            if "azurefd.net" in old_url:
                print(f"  SKIP  {pn} — already has CDN URL")
                continue

            print(f"  FETCH {pn} ...", end=" ", flush=True)
            img_url, canonical = fetch_image_url_playwright(page, product)

            if img_url and "azurefd.net" in img_url:
                product["image_url"] = img_url
                if canonical and canonical != product.get("url"):
                    product["url"] = canonical
                print(f"OK ({img_url[:70]})")
                updated += 1
            else:
                print(f"not found (tried: {product.get('url', 'N/A')})")

            time.sleep(0.5)  # be polite

        browser.close()

    DATA_PATH.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone — updated {updated}/{len(products)} image URLs.")


if __name__ == "__main__":
    main()
