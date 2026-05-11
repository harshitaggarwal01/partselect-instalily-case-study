from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.cart import Cart, CartItem
from app.services.cart_store import cart_store
from app.tools.products import get_product

router = APIRouter()


class AddItemBody(BaseModel):
    part_number: str


@router.get("/", response_model=Cart)
async def get_cart(request: Request) -> Cart:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await cart_store.get_cart(user.id)


@router.post("/items", response_model=Cart)
async def add_item(body: AddItemBody, request: Request) -> Cart:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    product = get_product(body.part_number)
    if product is not None:
        item = CartItem(
            part_number=body.part_number.upper(),
            name=product.name or f"Part {body.part_number}",
            url=product.url,
            image_url=product.image_url,
            price=product.price,
            quantity=1,
        )
    else:
        item = CartItem(
            part_number=body.part_number.upper(),
            name=f"Part {body.part_number}",
            quantity=1,
        )

    return await cart_store.add_item(user.id, item)


@router.delete("/items/{part_number}", response_model=Cart)
async def remove_item(part_number: str, request: Request) -> Cart:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await cart_store.remove_item(user.id, part_number)


@router.post("/clear", response_model=Cart)
async def clear_cart(request: Request) -> Cart:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await cart_store.clear_cart(user.id)


@router.get("/checkout-links")
async def checkout_links(request: Request) -> dict:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    cart = await cart_store.get_cart(user.id)
    links = []
    for item in cart.items:
        if item.url:
            links.append(item.url)
        else:
            links.append(
                f"https://www.partselect.com/search.aspx?SearchTerm={item.part_number}"
            )
    return {"links": links}
