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
}


async def detect_intent(message: str) -> IntentType:
    msg = message.lower()

    if any(k in msg for k in _TROUBLESHOOT):
        return "troubleshooting"
    if any(k in msg for k in _COMPAT):
        return "compatibility"
    if any(k in msg for k in _INSTALL):
        return "install"
    if re.search(r"\bPS\d+\b", msg, re.I) or any(k in msg for k in _DOMAIN):
        return "product_info"

    return "out_of_scope"
