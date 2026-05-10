from __future__ import annotations

import json
from pathlib import Path

from app.models.schemas import Product

_DATA_PATH = Path(__file__).parent.parent / "data" / "products.json"

_products: dict[str, Product] = {}


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
