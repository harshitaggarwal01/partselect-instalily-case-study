from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, MODEL_FAST, chat_claude
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ProductInfoResponse,
)
from app.services.agents import (
    CompatibilityAgent,
    InstallAgent,
    ProductInfoAgent,
    TroubleshootingAgent,
)
from app.services.intent_router import IntentType, _PART_NUMBER_RE, detect_intent

_AGENTS = {
    "install": InstallAgent(),
    "compatibility": CompatibilityAgent(),
    "product_info": ProductInfoAgent(),
    "troubleshooting": TroubleshootingAgent(),
}

_OUT_OF_SCOPE_RESPONSE = ProductInfoResponse(
    type="product_info",
    text=(
        "I specialize in refrigerator and dishwasher parts only. "
        "Try asking about a specific part number, how to install a part, "
        "whether a part fits your model, or how to fix a common issue."
    ),
    products=[],
)

_MODEL_RE = re.compile(r"\b([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)\b")

# ---------------------------------------------------------------------------
# Session store (in-memory, suitable for single-process dev/demo)
# ---------------------------------------------------------------------------

_session_store: Dict[str, Tuple[List[ChatMessage], datetime]] = {}
_SESSION_TTL = timedelta(minutes=30)
_MAX_SESSION_MESSAGES = 10


def _get_session_history(session_id: str) -> List[ChatMessage]:
    now = datetime.utcnow()
    expired = [
        sid for sid, (_, ts) in list(_session_store.items())
        if now - ts > _SESSION_TTL
    ]
    for sid in expired:
        del _session_store[sid]
    entry = _session_store.get(session_id)
    return list(entry[0]) if entry else []


def _save_session(session_id: str, messages: List[ChatMessage]) -> None:
    _session_store[session_id] = (messages[-_MAX_SESSION_MESSAGES:], datetime.utcnow())


# ---------------------------------------------------------------------------
# Follow-up detection
# ---------------------------------------------------------------------------

_FOLLOWUP_PROMPT = """\
Classify whether the user's new message is a follow-up about the SAME topic \
from the prior conversation, or the start of a NEW topic.

FOLLOW-UP (same topic):
- "What does step 3 mean?" (asking about a step from prior response)
- "Can you explain that more?" (elaborating on prior response)
- "Why would I need to do that?" (questioning a prior step)
- "What if that doesn't work?" (continuing troubleshooting thread)

NEW TOPIC (different topic):
- "What about the water filter?" (introduces a different component)
- "Now how do I fix the dishwasher?" (different appliance/issue)
- "Can you help with my compressor?" (new component not in prior response)

Last assistant response excerpt: {prev_summary}
User's new message: {user_msg}

Reply with exactly one word: "followup" or "new_topic"
"""

_FOLLOWUP_ANSWER_SYSTEM = (
    DOMAIN_SYSTEM_PROMPT
    + "\n\nThe user is asking a follow-up question. Answer using only the conversation "
    "history — do not introduce new information. Be concise and direct."
)

_CLARIFICATION_PROMPT = """\
A customer sent a vague message to PartSelect appliance parts support.
Ask ONE short clarifying question to understand their specific need.
Focus on: which appliance (refrigerator or dishwasher) if unclear, or what specific \
symptom or part they need help with.
Reply with only the question, nothing else.

Customer message: {user_msg}
"""


async def _is_followup(user_msg: str, history: List[ChatMessage]) -> bool:
    if len(history) < 2:
        return False
    last_assistant: Optional[ChatMessage] = next(
        (m for m in reversed(history[:-1]) if m.role == "assistant"), None
    )
    if last_assistant is None:
        return False
    words = user_msg.strip().split()
    if len(words) > 20:
        return False
    if _PART_NUMBER_RE.search(user_msg) or _MODEL_RE.search(user_msg):
        return False
    raw = await chat_claude(
        "You classify customer support messages. Reply with one word only.",
        [{"role": "user", "content": _FOLLOWUP_PROMPT.format(
            prev_summary=last_assistant.content[:300],
            user_msg=user_msg,
        )}],
        max_tokens=5,
        model=MODEL_FAST,
    )
    return raw.strip().lower().startswith("followup")


def _is_vague_query(user_msg: str, intent: IntentType) -> bool:
    if intent != "product_info":
        return False
    words = user_msg.strip().split()
    if len(words) > 4:
        return False
    if _PART_NUMBER_RE.search(user_msg) or _MODEL_RE.search(user_msg):
        return False
    return True


async def _answer_followup(history: List[ChatMessage]) -> ChatResponse:
    msgs = [
        {"role": m.role, "content": m.content}
        for m in history
        if m.role in ("user", "assistant")
    ]
    raw = await chat_claude(
        _FOLLOWUP_ANSWER_SYSTEM,
        msgs,
        max_tokens=512,
        model=MODEL_FAST,
    )
    return ProductInfoResponse(type="product_info", text=raw.strip(), products=[])


async def _ask_clarification(user_msg: str) -> ChatResponse:
    question = await chat_claude(
        DOMAIN_SYSTEM_PROMPT,
        [{"role": "user", "content": _CLARIFICATION_PROMPT.format(user_msg=user_msg)}],
        max_tokens=128,
        model=MODEL_FAST,
    )
    return ProductInfoResponse(
        type="product_info", text=question.strip(), products=[]
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_agent(request: ChatRequest) -> ChatResponse:
    """Detect intent, dispatch to the correct agent."""
    new_user_msg = request.messages[-1]
    user_msg = new_user_msg.content

    # Build full message history (session-aware)
    if request.session_id:
        prior = _get_session_history(request.session_id)
        all_messages = prior + [new_user_msg]
    else:
        all_messages = list(request.messages)

    history = all_messages[-5:]

    # Follow-up detection — skip full pipeline if continuing prior topic
    if await _is_followup(user_msg, history):
        response = await _answer_followup(history)
    else:
        intent: IntentType = await detect_intent(user_msg)

        if _is_vague_query(user_msg, intent):
            response = await _ask_clarification(user_msg)
        else:
            agent = _AGENTS.get(intent)
            response = (
                await agent.run(request, user_msg, history)
                if agent is not None
                else _OUT_OF_SCOPE_RESPONSE
            )

    # Persist updated history in session store
    if request.session_id:
        assistant_text = getattr(response, "text", "")
        updated = all_messages + [ChatMessage(role="assistant", content=assistant_text)]
        _save_session(request.session_id, updated)

    return response
