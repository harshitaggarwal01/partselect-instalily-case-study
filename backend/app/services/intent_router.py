from __future__ import annotations

import re
from typing import Literal

IntentType = Literal["install", "compatibility", "product_info", "troubleshooting", "out_of_scope"]

_TROUBLESHOOT = {
    "not working", "not work", "broken", "issue", "problem", "won't", "wont",
    "doesn't work", "doesnt work", "fix", "repair", "stopped", "no ice",
    "not cooling", "not cold", "not cleaning", "not draining", "leaking",
    "making noise", "loud noise", "won't start", "wont start",
}
_COMPAT = {
    "compatible", "compatibility", "fit", "fits", "work with", "works with",
    "will it fit", "does it fit", "match", "matches",
}
_INSTALL = {
    "install", "installation", "replace", "replacing", "replacement",
    "how to put", "put in", "how do i install", "how to install",
    "how to replace", "swap",
}
_DOMAIN = {
    "refrigerator", "fridge", "dishwasher", "washer", "appliance",
    "part", "parts", "repair",
    "ice maker", "water filter", "spray arm", "door latch", "thermostat",
    "freezer", "evaporator", "compressor", "condenser", "gasket", "drain pump",
}

# Matches PS-prefixed, WP-prefixed, W-numeric, and bare 8+-digit part numbers
_PART_NUMBER_RE = re.compile(
    r"\b(PS\d{6,}|WP[A-Z0-9]{5,}|W[0-9]{5,}[A-Z0-9]*|[0-9]{8,})\b", re.I
)

_FEW_SHOT_PROMPT = """\
Classify the customer message into exactly one of these categories:
install, compatibility, product_info, troubleshooting, out_of_scope

Examples:
"How do I replace the ice maker?" → install
"Will PS11752778 fit my WDT780SAEM1 dishwasher?" → compatibility
"What is part W10195682?" → product_info
"My dishwasher won't drain after the last cycle" → troubleshooting
"What time does your store close?" → out_of_scope
"Can you recommend a good refrigerator?" → out_of_scope

Message: {message}
Reply with only the single category word, nothing else."""


async def classify_intent_llm(message: str) -> IntentType:
    """Few-shot LLM classifier for ambiguous domain messages.

    Only called when keyword rules are inconclusive. Uses haiku for speed/cost.
    """
    from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, MODEL_FAST, chat_claude

    raw = await chat_claude(
        DOMAIN_SYSTEM_PROMPT,
        [{"role": "user", "content": _FEW_SHOT_PROMPT.format(message=message)}],
        max_tokens=10,
        model=MODEL_FAST,
    )
    result = raw.strip().lower().split()[0] if raw.strip() else ""
    valid: set = {"install", "compatibility", "product_info", "troubleshooting", "out_of_scope"}
    return result if result in valid else "product_info"  # type: ignore[return-value]


async def detect_intent(message: str) -> IntentType:
    """Classify a user message into one of five intent categories.

    Priority: keyword fast-path → LLM classifier (domain only) → out_of_scope.
    """
    msg = message.lower()

    # Fast-path keyword rules (deterministic, no API call)
    if any(k in msg for k in _TROUBLESHOOT):
        return "troubleshooting"
    if any(k in msg for k in _COMPAT):
        return "compatibility"
    if any(k in msg for k in _INSTALL):
        return "install"

    # Domain check — part numbers (any format) or appliance keywords
    in_domain = bool(_PART_NUMBER_RE.search(msg)) or any(k in msg for k in _DOMAIN)
    if in_domain:
        return await classify_intent_llm(message)

    return "out_of_scope"
