from __future__ import annotations

import re

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, chat_claude
from app.models.schemas import ChatRequest, CompatibilityResponse
from app.tools.compatibility import check_compatibility
from app.tools.products import get_product


async def handle_compatibility(request: ChatRequest, user_msg: str) -> CompatibilityResponse:
    part_match = re.search(r"\b(PS\d+|WP[A-Z0-9]+|W[0-9]{6,})\b", user_msg, re.I)
    # Model numbers: 2+ capital letters followed by 3+ digits and optional alphanumerics
    model_match = re.search(r"\b([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)\b", user_msg)

    part_number = part_match.group(0).upper() if part_match else None
    model_number = model_match.group(0).upper() if model_match else None

    product = get_product(part_number) if part_number else None

    if part_number and model_number:
        status = check_compatibility(model_number, part_number)
    else:
        status = "unknown"

    status_text = {
        "compatible": f"Yes, part {part_number} is compatible with model {model_number}.",
        "not_compatible": f"No, part {part_number} is not compatible with model {model_number}.",
        "unknown": "I could not determine compatibility from the available data.",
    }[status]

    context = (
        f"Compatibility check result: {status_text}\n"
        f"Part: {part_number or 'not specified'}\n"
        f"Model: {model_number or 'not specified'}\n"
    )
    if product:
        context += f"Part details: {product.name} — {product.description}"

    messages = [
        {
            "role": "user",
            "content": (
                f"Customer asked: {user_msg}\n\n{context}\n\n"
                "Provide a brief, helpful compatibility answer based on the above data."
            ),
        }
    ]

    details = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages)

    return CompatibilityResponse(
        type="compatibility",
        text=status_text,
        part=product,
        model_number=model_number,
        status=status,
        details=details,
    )
