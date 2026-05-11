from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.models.cart import Cart, CartItem

_DATA_PATH = Path(__file__).parent.parent / "data" / "carts.json"


def _load_data() -> dict:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"carts": []}


def _save_data(data: dict) -> None:
    _DATA_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class CartStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._data: dict = _load_data()

    def _find_cart_dict(self, user_id: str) -> dict | None:
        for c in self._data.get("carts", []):
            if c.get("user_id") == user_id:
                return c
        return None

    async def get_cart(self, user_id: str) -> Cart:
        cart_dict = self._find_cart_dict(user_id)
        if cart_dict is None:
            return Cart(user_id=user_id, items=[])
        return Cart(**cart_dict)

    async def add_item(self, user_id: str, item: CartItem) -> Cart:
        async with self._lock:
            cart_dict = self._find_cart_dict(user_id)
            if cart_dict is None:
                cart_dict = {"user_id": user_id, "items": []}
                self._data.setdefault("carts", []).append(cart_dict)

            # Check if part already in cart
            for existing in cart_dict["items"]:
                if existing.get("part_number") == item.part_number:
                    existing["quantity"] = existing.get("quantity", 1) + 1
                    _save_data(self._data)
                    return Cart(**cart_dict)

            cart_dict["items"].append(item.model_dump())
            _save_data(self._data)
            return Cart(**cart_dict)

    async def remove_item(self, user_id: str, part_number: str) -> Cart:
        async with self._lock:
            cart_dict = self._find_cart_dict(user_id)
            if cart_dict is None:
                return Cart(user_id=user_id, items=[])
            cart_dict["items"] = [
                i for i in cart_dict["items"]
                if i.get("part_number") != part_number
            ]
            _save_data(self._data)
            return Cart(**cart_dict)

    async def clear_cart(self, user_id: str) -> Cart:
        async with self._lock:
            cart_dict = self._find_cart_dict(user_id)
            if cart_dict is not None:
                cart_dict["items"] = []
                _save_data(self._data)
            return Cart(user_id=user_id, items=[])


cart_store = CartStore()
