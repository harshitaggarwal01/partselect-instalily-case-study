"""Scrape part data from PartSelect to update or expand products.json.

Run offline to add new parts to the catalog. Pass part numbers as arguments.

Usage:
    cd backend
    python scripts/scrape_partselect.py PS11752778 W10295370A WPW10190965
    python scripts/scrape_partselect.py --input part_numbers.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

DATA_PATH = Path(__file__).parent.parent / "app" / "data" / "products.json"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

PS_BASE = "https://www.partselect.com"


def find_part_url(client: httpx.Client, part_number: str) -> str | None:
    """Search PartSelect for a part number and return the product page URL."""
    search_url = f"{PS_BASE}/search.aspx?SearchTerm={part_number}"
    try:
        resp = client.get(search_url, timeout=8.0)
        if resp.status_code != 200:
            return None
        # Find a part page link in search results
        match = re.search(
            r'href="(/(?:PS\d+|' + re.escape(part_number) + r')[^"]+\.htm)"',
            resp.text,
            re.I,
        )
        return f"{PS_BASE}{match.group(1)}" if match else None
    except Exception as exc:
        print(f"  ERROR searching {part_number}: {exc}", file=sys.stderr)
        return None


def scrape_part(client: httpx.Client, part_number: str) -> dict | None:
    """Fetch and parse a PartSelect product page."""
    page_url = find_part_url(client, part_number)
    if not page_url:
        print(f"  NOT FOUND: {part_number}")
        return None

    try:
        resp = client.get(page_url, timeout=8.0)
        if resp.status_code != 200:
            return None
        html = resp.text

        # Part name from h1
        h1 = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html)
        name = h1.group(1).strip() if h1 else f"Part {part_number}"

        # Image from Azure CDN
        img = re.search(
            r"(partselectcom-[^/]+\.azurefd\.net/[^\s\"']+\.jpg)", html
        )
        image_url = f"https://{img.group(1)}" if img else None

        # Price
        price_m = re.search(
            r'class="[^"]*price[^"]*"[^>]*>\s*\$([0-9]+\.[0-9]{2})', html, re.I
        )
        price = float(price_m.group(1)) if price_m else None

        # Description — look for meta description or first paragraph
        desc_m = re.search(r'<meta name="description" content="([^"]+)"', html)
        description = desc_m.group(1).strip() if desc_m else None

        return {
            "part_number": part_number.upper(),
            "name": name,
            "price": price,
            "image_url": image_url,
            "url": page_url,
            "description": description,
        }
    except Exception as exc:
        print(f"  ERROR scraping {page_url}: {exc}", file=sys.stderr)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape PartSelect parts into products.json")
    parser.add_argument("parts", nargs="*", help="Part numbers to scrape")
    parser.add_argument("--input", help="File with one part number per line")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing entries")
    args = parser.parse_args()

    part_numbers: list[str] = list(args.parts)
    if args.input:
        part_numbers += Path(args.input).read_text().splitlines()
    part_numbers = [p.strip().upper() for p in part_numbers if p.strip()]

    if not part_numbers:
        print("No part numbers provided. Use: python scrape_partselect.py PS11752778 ...")
        sys.exit(1)

    existing = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    existing_map = {p["part_number"].upper(): p for p in existing}

    added, updated_count = 0, 0

    with httpx.Client(headers=BROWSER_HEADERS, follow_redirects=True) as client:
        for pn in part_numbers:
            if pn in existing_map and not args.overwrite:
                print(f"  SKIP  {pn} — already in catalog (use --overwrite to replace)")
                continue

            print(f"  FETCH {pn} ...", end=" ", flush=True)
            data = scrape_part(client, pn)
            if data:
                if pn in existing_map:
                    existing_map[pn].update(data)
                    updated_count += 1
                    print(f"UPDATED — {data['name']}")
                else:
                    existing_map[pn] = data
                    added += 1
                    print(f"ADDED — {data['name']}")
            else:
                print("failed")

            time.sleep(1.0)  # polite rate limit

    products = list(existing_map.values())
    DATA_PATH.write_text(json.dumps(products, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nDone — added {added}, updated {updated_count} parts. Total: {len(products)}")


if __name__ == "__main__":
    main()
