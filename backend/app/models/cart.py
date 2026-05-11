from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class CartItem(BaseModel):
    part_number: str
    name: str
    url: Optional[str] = None
    image_url: Optional[str] = None
    price: Optional[float] = None
    quantity: int = 1


class Cart(BaseModel):
    user_id: str
    items: list[CartItem] = []
