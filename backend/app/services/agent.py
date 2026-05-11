from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, MODEL_FAST, chat_claude
from app.models.schemas import ChatMessage, ChatRequest, ChatResponse
from app.services.thread_store import thread_store
from app.services.agents import (
    CompatibilityAgent,
    InstallAgent,
    ProductInfoAgent,
    TroubleshootingAgent,
)

logger = logging.getLogger("partselect_agent.agent")

# --- Session cache (RAM, keyed by thread_id) ---
# Stores recent messages to avoid re-reading threads.json each turn
_session_cache: Dict[str, Tuple[List[ChatMessage], datetime]] = {}
_SESSION_TTL = timedelta(minutes=30)


def _get_cached_messages(thread_id: str) -> Optional[List[ChatMessage]]:
    entry = _session_cache.get(thread_id)
    if entry and datetime.utcnow() - entry[1] < _SESSION_TTL:
        return entry[0]
    return None


def _set_cached_messages(thread_id: str, messages: List[ChatMessage]) -> None:
    _session_cache[thread_id] = (messages, datetime.utcnow())


# --- Response cache (FIFO, max 100 entries) ---
_response_cache: Dict[tuple, ChatResponse] = {}
_response_cache_order: List[tuple] = []
_CACHE_MAX = 100


def _cache_key(intent: str, msg: str, appliance: Optional[str]) -> tuple:
    return (intent, msg.lower().strip()[:120], appliance or "")


def _get_cached_response(key: tuple) -> Optional[ChatResponse]:
    return _response_cache.get(key)


def _set_cached_response(key: tuple, response: ChatResponse) -> None:
    if key in _response_cache:
        return
    if len(_response_cache_order) >= _CACHE_MAX:
        evict = _response_cache_order.pop(0)
        _response_cache.pop(evict, None)
    _response_cache[key] = response
    _response_cache_order.append(key)


# --- Combined intent/flags classifier ---
async def _classify_intent_and_flags(
    user_msg: str,
    history_tail: List[ChatMessage],
    last_response_type: Optional[str],
) -> dict:
    """Returns {intent, is_followup, needs_clarification}.

    Uses keyword fast-path first; falls back to a single haiku call for ambiguous cases.
    """
    import re
    lower = user_msg.lower()

    # Broader part-number pattern: PS, WP, W-prefixed, letter+digits, pure digits
    _BROAD_PART_RE = re.compile(
        r"\b(PS\d{5,}|WP[A-Z0-9]{4,}|W[0-9]{5,}[A-Z0-9]*"
        r"|[A-Z]{1,4}[0-9]{4,}[A-Z0-9-]*|[0-9]{6,})\b",
        re.I,
    )
    has_part = bool(_BROAD_PART_RE.search(user_msg))

    # Import domain keywords from intent_router
    from app.services.intent_router import _DOMAIN
    in_domain = has_part or any(k in lower for k in _DOMAIN)

    if not in_domain:
        return {"intent": "out_of_scope", "is_followup": False, "needs_clarification": False}

    # Install/compatibility fast path
    if has_part:
        if any(k in lower for k in ("install", "replace", "change", "fit", "put in", "remove")):
            return {"intent": "install", "is_followup": False, "needs_clarification": False}
        model_re = re.compile(r"\b([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)\b")
        if model_re.search(user_msg):
            return {"intent": "compatibility", "is_followup": False, "needs_clarification": False}
        return {"intent": "product_info", "is_followup": False, "needs_clarification": False}

    # Troubleshooting fast path
    trouble_kws = (
        "not working", "broken", "leaking", "not cooling", "not cleaning",
        "won't start", "wont start", "not draining", "not dispensing", "not making ice",
        "not spinning", "smells", "noisy", "error", "symptom", "problem", "issue", "repair",
    )
    if any(k in lower for k in trouble_kws):
        return {"intent": "troubleshooting", "is_followup": False, "needs_clarification": False}

    # Haiku for ambiguous cases
    history_str = "\n".join(f"{m.role}: {m.content[:100]}" for m in history_tail[-4:])
    prompt = (
        f"Classify this user message in an appliance parts chat.\n\n"
        f"Recent conversation:\n{history_str}\n"
        f"Last assistant response type: {last_response_type or 'none'}\n"
        f"User message: {user_msg}\n\n"
        f"Return ONLY this JSON (no markdown):\n"
        f'{{ "intent": "install|compatibility|product_info|troubleshooting|out_of_scope", '
        f'"is_followup": true/false, "needs_clarification": true/false }}\n\n'
        f"Rules:\n"
        f"- is_followup=true ONLY if message directly references prior response (e.g. step 3, tell me more)\n"
        f"- needs_clarification=true if too vague for specific advice (e.g. 'my appliance is weird')\n"
        f"- out_of_scope if not about refrigerators/dishwashers"
    )
    try:
        raw = await chat_claude(
            DOMAIN_SYSTEM_PROMPT,
            [{"role": "user", "content": prompt}],
            max_tokens=60,
            model=MODEL_FAST,
        )
        return json.loads(raw.strip())
    except Exception:
        return {"intent": "product_info", "is_followup": False, "needs_clarification": False}


# --- Follow-up answering (no retrieval) ---
async def _answer_followup(history: List[ChatMessage]) -> ChatResponse:
    from app.models.schemas import ProductInfoResponse

    context = "\n".join(f"{m.role}: {m.content}" for m in history[-6:])
    prompt = (
        "The user is asking a follow-up question about the previous response. "
        "Answer directly using only the conversation context above. "
        "Do not perform any new searches or mention sources."
    )
    messages = [{"role": "user", "content": f"Conversation:\n{context}\n\n{prompt}"}]
    text = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages, max_tokens=400, model=MODEL_FAST)
    return ProductInfoResponse(type="product_info", text=text, products=[])


# --- Clarification asking ---
async def _ask_clarification(user_msg: str) -> ChatResponse:
    from app.models.schemas import ProductInfoResponse

    prompt = (
        f"The user said: '{user_msg}'\n"
        "This is too vague to give specific advice. "
        "Reply briefly acknowledging you need more info, then list what would help as markdown bullets:\n"
        "- Appliance type (refrigerator or dishwasher)\n"
        "- The specific symptom or problem\n"
        "- Part number, if they have one\n"
        "Keep the full response under 60 words."
    )
    messages = [{"role": "user", "content": prompt}]
    text = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages, max_tokens=100, model=MODEL_FAST)
    return ProductInfoResponse(type="product_info", text=text, products=[])


# --- History summarization ---
async def _summarize_messages(messages: List[ChatMessage]) -> ChatMessage:
    """Summarize a list of messages into a single assistant message."""
    conv = "\n".join(f"{m.role}: {m.content}" for m in messages)
    prompt = f"Summarize this conversation excerpt in 2-3 sentences:\n\n{conv}"
    text = await chat_claude(
        DOMAIN_SYSTEM_PROMPT,
        [{"role": "user", "content": prompt}],
        max_tokens=200,
        model=MODEL_FAST,
    )
    return ChatMessage(role="assistant", content=f"[Summary of prior conversation: {text}]")


# --- Main orchestrator ---
_AGENTS = {
    "install": InstallAgent(),
    "compatibility": CompatibilityAgent(),
    "product_info": ProductInfoAgent(),
    "troubleshooting": TroubleshootingAgent(),
}


async def run_agent(request: ChatRequest, user_id: str) -> ChatResponse:
    # 1. Determine thread_id — create new thread if none provided
    thread_id = request.thread_id
    if not thread_id:
        thread = await thread_store.create_thread(user_id=user_id, title="New Conversation")
        thread_id = thread.id

    # 2. Load history (session cache → thread store fallback)
    history = _get_cached_messages(thread_id)
    if history is None:
        history = await thread_store.get_recent_messages(thread_id, limit=20)

    # 3. Add current user message
    user_msg_obj = ChatMessage(role="user", content=request.messages[-1].content)
    history_with_new = history + [user_msg_obj]

    # 4. Summarize if history is long (>20 messages: summarize oldest 10)
    if len(history_with_new) > 20:
        to_summarize = history_with_new[:10]
        summary_msg = await _summarize_messages(to_summarize)
        history_with_new = [summary_msg] + history_with_new[10:]
        await thread_store.update_messages_for_thread(thread_id, history_with_new)

    user_msg = user_msg_obj.content

    # 5. Classify intent + flags
    flags = await _classify_intent_and_flags(user_msg, history_with_new[-6:], None)
    intent = flags.get("intent", "product_info")
    is_followup = flags.get("is_followup", False)
    needs_clarification = flags.get("needs_clarification", False)

    logger.info(
        "run_agent: intent=%s followup=%s clarify=%s", intent, is_followup, needs_clarification
    )

    # 6. Build cache key and check response cache (only for non-followup, non-clarification)
    cache_key: Optional[tuple] = None
    if not is_followup and not needs_clarification and intent != "out_of_scope":
        appliance: Optional[str] = None
        if "refrigerator" in user_msg.lower() or "fridge" in user_msg.lower():
            appliance = "refrigerator"
        elif "dishwasher" in user_msg.lower():
            appliance = "dishwasher"
        cache_key = _cache_key(intent, user_msg, appliance)
        cached = _get_cached_response(cache_key)
        if cached:
            logger.info("run_agent: cache hit")
            cached_with_thread = cached.model_copy(update={"thread_id": thread_id})
            assistant_text = getattr(cached_with_thread, "text", "")
            assistant_msg = ChatMessage(role="assistant", content=assistant_text)
            new_history = history_with_new + [assistant_msg]
            await thread_store.append_messages(thread_id, [user_msg_obj, assistant_msg])
            _set_cached_messages(thread_id, new_history[-10:])
            return cached_with_thread

    # 7. Handle follow-up
    if is_followup:
        response = await _answer_followup(history_with_new)
        response = response.model_copy(update={"thread_id": thread_id})
        assistant_msg = ChatMessage(role="assistant", content=response.text)
        await thread_store.append_messages(thread_id, [user_msg_obj, assistant_msg])
        _set_cached_messages(thread_id, (history_with_new + [assistant_msg])[-10:])
        if len(history) == 0:
            await thread_store.update_title(thread_id, user_msg[:50] + ("…" if len(user_msg) > 50 else ""))
        return response

    # 8. Handle vague → clarification
    if needs_clarification:
        response = await _ask_clarification(user_msg)
        response = response.model_copy(update={"thread_id": thread_id})
        assistant_msg = ChatMessage(role="assistant", content=response.text)
        await thread_store.append_messages(thread_id, [user_msg_obj, assistant_msg])
        _set_cached_messages(thread_id, (history_with_new + [assistant_msg])[-10:])
        if len(history) == 0:
            await thread_store.update_title(thread_id, user_msg[:50] + ("…" if len(user_msg) > 50 else ""))
        return response

    # 9. Out of scope
    if intent == "out_of_scope":
        from app.models.schemas import ProductInfoResponse

        text = (
            "I can only help with refrigerator and dishwasher parts. "
            "Please visit partselect.com for other appliances."
        )
        response = ProductInfoResponse(
            type="product_info", text=text, products=[], thread_id=thread_id
        )
        assistant_msg = ChatMessage(role="assistant", content=text)
        await thread_store.append_messages(thread_id, [user_msg_obj, assistant_msg])
        _set_cached_messages(thread_id, (history_with_new + [assistant_msg])[-10:])
        return response

    # 10. Route to agent
    agent = _AGENTS.get(intent, _AGENTS["product_info"])
    routed_request = request.model_copy(
        update={"messages": history_with_new, "thread_id": thread_id}
    )
    response = await agent.run(routed_request, user_msg, history_with_new)

    # Set thread_id on response
    response = response.model_copy(update={"thread_id": thread_id})

    # 11. Cache + persist
    if cache_key is not None:
        _set_cached_response(cache_key, response)

    assistant_text = getattr(response, "text", "")
    assistant_msg = ChatMessage(role="assistant", content=assistant_text)
    new_history = history_with_new + [assistant_msg]
    await thread_store.append_messages(thread_id, [user_msg_obj, assistant_msg])
    _set_cached_messages(thread_id, new_history[-10:])

    # Auto-title thread after first message
    if len(history) == 0:
        title = user_msg[:50] + ("…" if len(user_msg) > 50 else "")
        await thread_store.update_title(thread_id, title)

    return response
