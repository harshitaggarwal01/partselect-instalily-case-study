from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import httpx

from app.models.schemas import Product

_DATA_PATH = Path(__file__).parent.parent / "data" / "products.json"

_products: dict[str, Product] = {}
_live_cache: dict[str, Optional[Product]] = {}

_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


def _ensure_loaded() -> None:
    if not _products:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        for item in raw:
            p = Product(**item)
            _products[p.part_number.upper()] = p


def get_product(part_number: str) -> Product | None:
    _ensure_loaded()
    return _products.get(part_number.upper())


def search_products(query: str | None = None, part_number: str | None = None) -> list[Product]:
    _ensure_loaded()
    if part_number:
        result = get_product(part_number)
        return [result] if result else []
    if not query:
        return list(_products.values())
    q = query.lower()
    return [
        p for p in _products.values()
        if q in (p.name or "").lower()
        or q in (p.description or "").lower()
        or q in p.part_number.lower()
    ]


async def lookup_part_live(part_number: str) -> Optional[Product]:
    """Try to fetch part info from PartSelect for unknown part numbers.

    Returns None on timeout, HTTP error, or if the part genuinely doesn't exist.
    Results are cached in-memory for the process lifetime.
    """
    pn = part_number.upper()
    if pn in _live_cache:
        return _live_cache[pn]

    search_url = f"https://www.partselect.com/search.aspx?SearchTerm={pn}"
    try:
        async with httpx.AsyncClient(
            timeout=2.0, headers=_BROWSER_HEADERS, follow_redirects=True
        ) as client:
            resp = await client.get(search_url)
            if resp.status_code != 200:
                _live_cache[pn] = None
                return None

            html = resp.text
            # Look for a part page URL in the search results HTML
            url_match = re.search(
                r'href="(/(?:PS\d+|' + re.escape(pn) + r')[^"]+\.htm)"',
                html,
                re.I,
            )
            if not url_match:
                _live_cache[pn] = None
                return None

            part_url = "https://www.partselect.com" + url_match.group(1)
            resp2 = await client.get(part_url)
            html2 = resp2.text

            # Extract part name from <h1>
            h1 = re.search(r"<h1[^>]*>\s*([^<]+?)\s*</h1>", html2)
            name = h1.group(1).strip() if h1 else f"Part {pn}"

            # Extract image from Azure CDN
            img = re.search(r"(partselectcom-[^/]+\.azurefd\.net/[^\"'\s]+\.jpg)", html2)
            image_url = f"https://{img.group(1)}" if img else None

            # Extract price
            price_m = re.search(r"class=\"[^\"]*price[^\"]*\"[^>]*>\s*\$([0-9]+\.[0-9]{2})", html2, re.I)
            price = float(price_m.group(1)) if price_m else None

            product = Product(
                part_number=pn,
                name=name,
                price=price,
                image_url=image_url,
                url=part_url,
                description=None,
            )
            _live_cache[pn] = product
            return product
    except Exception:
        _live_cache[pn] = None
        return None
