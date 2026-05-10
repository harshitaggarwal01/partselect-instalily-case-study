from __future__ import annotations

import json
import re

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, chat_claude_json
from app.models.schemas import ChatRequest, InstallResponse, InstallStep, Product
from app.tools.guides import find_install_guides
from app.tools.products import get_product

_INSTALL_SCHEMA = """
{
  "text": "string — friendly intro sentence",
  "steps": [
    {"step_number": 1, "instruction": "string", "caution": "string or null"}
  ],
  "sources": ["string — URL or guide id"]
}
"""


async def handle_install(request: ChatRequest, user_msg: str) -> InstallResponse:
    part_match = re.search(r"\b(PS\d+|WP[A-Z0-9]+|W[0-9]{6,})\b", user_msg, re.I)
    part_number = part_match.group(0).upper() if part_match else None

    product = get_product(part_number) if part_number else None
    guides = find_install_guides(part_number=part_number)

    context_parts = []
    if product:
        context_parts.append(
            f"Part: {product.part_number} — {product.name}\n"
            f"Description: {product.description}"
        )
    if guides:
        for g in guides[:2]:
            steps_text = "\n".join(
                f"  Step {s['step_number']}: {s['instruction']}"
                + (f" CAUTION: {s['caution']}" if s.get("caution") else "")
                for s in g.get("steps", [])
            )
            context_parts.append(f"Guide: {g['title']}\n{steps_text}")

    context = "\n\n".join(context_parts) if context_parts else "No specific guide found."

    messages = [
        {
            "role": "user",
            "content": (
                f"Customer asked: {user_msg}\n\n"
                f"Context from our knowledge base:\n{context}\n\n"
                "Return installation instructions as JSON."
            ),
        }
    ]

    data = await chat_claude_json(DOMAIN_SYSTEM_PROMPT, messages, _INSTALL_SCHEMA)

    if data.get("parse_error"):
        return InstallResponse(
            type="install",
            text=data.get("text", "I found some installation information but could not format it properly."),
            part=product,
            steps=[],
            sources=[g.get("url", "") for g in guides],
        )

    steps = [
        InstallStep(
            step_number=s.get("step_number", i + 1),
            instruction=s.get("instruction", ""),
            caution=s.get("caution"),
        )
        for i, s in enumerate(data.get("steps", []))
    ]
    sources = data.get("sources") or [g.get("url", "") for g in guides]

    return InstallResponse(
        type="install",
        text=data.get("text", "Here are the installation instructions:"),
        part=product,
        steps=steps,
        sources=[s for s in sources if s],
    )
