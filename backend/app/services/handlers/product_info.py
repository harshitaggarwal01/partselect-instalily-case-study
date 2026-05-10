from __future__ import annotations

import re

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, chat_claude
from app.models.schemas import ChatRequest, Product, ProductInfoResponse
from app.tools.products import get_product, search_products


async def handle_product_info(request: ChatRequest, user_msg: str) -> ProductInfoResponse:
    # Try to extract a part number
    match = re.search(r"\b(PS\d+|W[A-Z0-9]+|[0-9]{6,})\b", user_msg, re.I)
    if match:
        products = search_products(part_number=match.group(0))
    else:
        products = search_products(query=user_msg)

    products = products[:3]  # cap results

    if products:
        context = "Available product information:\n" + "\n".join(
            f"- {p.part_number}: {p.name}, ${p.price or 'N/A'} — {p.description}"
            for p in products
        )
    else:
        context = "No matching parts found in the catalog."

    messages = [
        {
            "role": "user",
            "content": (
                f"Customer asked: {user_msg}\n\n{context}\n\n"
                "Provide a concise, helpful response about these parts. "
                "If no parts were found, acknowledge that and invite the customer "
                "to try a different part number or description."
            ),
        }
    ]

    text = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages)

    return ProductInfoResponse(
        type="product_info",
        text=text,
        products=[Product(**p.model_dump()) for p in products],
    )
