from __future__ import annotations

import json
import re

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, chat_claude_json
from app.models.schemas import ChatRequest, TroubleshootStep, TroubleshootingResponse
from app.tools.guides import find_troubleshooting_guides

_TROUBLESHOOT_SCHEMA = """
{
  "text": "string — empathetic intro sentence acknowledging the issue",
  "issue": "string — short description of the identified issue",
  "steps": [
    {"step_number": 1, "description": "string"}
  ],
  "sources": ["string — URL or guide id"]
}
"""


def _detect_appliance(msg: str) -> str | None:
    m = msg.lower()
    if any(k in m for k in ("fridge", "refrigerator", "freezer", "ice maker")):
        return "refrigerator"
    if any(k in m for k in ("dishwasher",)):
        return "dishwasher"
    return None


async def handle_troubleshooting(request: ChatRequest, user_msg: str) -> TroubleshootingResponse:
    appliance_type = _detect_appliance(user_msg)
    guides = find_troubleshooting_guides(symptom=user_msg, appliance_type=appliance_type)

    context_parts = []
    for g in guides[:2]:
        steps_text = "\n".join(
            f"  Step {s['step_number']}: {s['description']}"
            for s in g.get("steps", [])
        )
        context_parts.append(f"Guide for '{g['symptom']}':\n{steps_text}")

    context = "\n\n".join(context_parts) if context_parts else "No specific guide found."

    messages = [
        {
            "role": "user",
            "content": (
                f"Customer asked: {user_msg}\n\n"
                f"Context from our knowledge base:\n{context}\n\n"
                "Return troubleshooting steps as JSON."
            ),
        }
    ]

    data = await chat_claude_json(DOMAIN_SYSTEM_PROMPT, messages, _TROUBLESHOOT_SCHEMA)

    if data.get("parse_error"):
        return TroubleshootingResponse(
            type="troubleshooting",
            text=data.get("text", "I found some troubleshooting information."),
            appliance_type=appliance_type,
            issue=None,
            steps=[],
            sources=[g.get("url", "") for g in guides],
        )

    steps = [
        TroubleshootStep(
            step_number=s.get("step_number", i + 1),
            description=s.get("description", ""),
        )
        for i, s in enumerate(data.get("steps", []))
    ]
    sources = data.get("sources") or [g.get("url", "") for g in guides]

    return TroubleshootingResponse(
        type="troubleshooting",
        text=data.get("text", "Here are some troubleshooting steps:"),
        appliance_type=appliance_type,
        issue=data.get("issue"),
        steps=steps,
        sources=[s for s in sources if s],
    )
