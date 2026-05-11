"""Agent classes — one per intent.

Each agent encapsulates retrieval + LLM call + response construction for its
intent. The orchestrator in agent.py instantiates one of each and routes to
the correct one based on detected intent.
"""
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger("partselect_agent.agents")

from app.llm.claude_client import DOMAIN_SYSTEM_PROMPT, chat_claude, chat_claude_json
from app.models.schemas import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    CompatibilityResponse,
    InstallResponse,
    InstallStep,
    Product,
    ProductInfoResponse,
    TroubleshootStep,
    TroubleshootingResponse,
)
from app.tools.compatibility import check_compatibility
from app.tools.guides import find_install_guides, find_troubleshooting_guides
from app.tools.products import get_product, lookup_part_live, search_products
from app.tools.rerank import rerank_chunks

_INSTALL_SCHEMA = """
{
  "text": "string — friendly intro sentence",
  "steps": [
    {"step_number": 1, "instruction": "string", "caution": "string or null"}
  ]
}
"""

_TROUBLESHOOT_SCHEMA = """
{
  "text": "string — empathetic intro sentence acknowledging the issue",
  "issue": "string — short description of the identified issue",
  "steps": [
    {"step_number": 1, "title": "string — 4-6 word action phrase", "description": "string"}
  ]
}
"""

_PART_RE = re.compile(r"\b(PS\d+|WP[A-Z0-9]+|W[0-9]{6,})\b", re.I)
_PART_BROAD_RE = re.compile(r"\b(PS\d+|W[A-Z0-9]+|[0-9]{6,})\b", re.I)
_MODEL_RE = re.compile(r"\b([A-Z]{2,}[0-9]{3,}[A-Z0-9]*)\b")


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseAgent(ABC):
    """Abstract base for all intent agents."""

    @abstractmethod
    async def run(
        self,
        request: ChatRequest,
        user_msg: str,
        history: List[ChatMessage],
    ) -> ChatResponse:
        ...

    def _build_messages(
        self, history: List[ChatMessage], context_injection: str
    ) -> List[dict]:
        """Convert conversation history to Anthropic message dicts and append RAG context.

        The context is injected into the last user message so Claude sees both
        the question and the relevant knowledge base excerpt in the same turn.
        """
        msgs = [
            {"role": m.role, "content": m.content}
            for m in history
            if m.role in ("user", "assistant")
        ]
        if msgs and msgs[-1]["role"] == "user":
            msgs[-1] = dict(msgs[-1])
            msgs[-1]["content"] = (
                msgs[-1]["content"]
                + f"\n\n[Knowledge base context]\n{context_injection}"
            )
        elif not msgs:
            msgs = [{"role": "user", "content": context_injection}]
        return msgs


# ---------------------------------------------------------------------------
# Install agent
# ---------------------------------------------------------------------------

class InstallAgent(BaseAgent):
    """Handles installation guide requests."""

    async def run(
        self,
        request: ChatRequest,
        user_msg: str,
        history: List[ChatMessage],
    ) -> InstallResponse:
        part_match = _PART_RE.search(user_msg)
        part_number: Optional[str] = part_match.group(0).upper() if part_match else None

        product = get_product(part_number) if part_number else None
        guides = await find_install_guides(part_number=part_number)
        logger.info("InstallAgent: guides from %s", {g.get("_source", "unknown") for g in guides})
        if len(guides) > 3:
            guides = await rerank_chunks(user_msg, guides, top_k=3)

        context_parts = []
        if product:
            context_parts.append(
                f"Part: {product.part_number} — {product.name}\n"
                f"Description: {product.description}"
            )
        if guides:
            for g in guides[:2]:
                steps_key = "steps" if "steps" in g else []
                steps_text = "\n".join(
                    f"  Step {s.get('step_number', i+1)}: "
                    f"{s.get('instruction', s.get('description', ''))}"
                    + (f" CAUTION: {s['caution']}" if s.get("caution") else "")
                    for i, s in enumerate(g.get("steps", []))
                )
                label = g.get("title") or g.get("text", "Guide")
                context_parts.append(f"Guide: {label}\n{steps_text}")

        context = "\n\n".join(context_parts) if context_parts else "No specific guide found."

        messages = self._build_messages(
            history,
            f"Context from our knowledge base:\n{context}\n\nReturn installation instructions as JSON.",
        )

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
        sources = [g.get("url", "") for g in guides]

        return InstallResponse(
            type="install",
            text=data.get("text", "Here are the installation instructions:"),
            part=product,
            steps=steps,
            sources=[s for s in sources if s],
            part_image_url=product.image_url if product else None,
        )


# ---------------------------------------------------------------------------
# Compatibility agent
# ---------------------------------------------------------------------------

class CompatibilityAgent(BaseAgent):
    """Handles part-model compatibility questions."""

    async def run(
        self,
        request: ChatRequest,
        user_msg: str,
        history: List[ChatMessage],
    ) -> CompatibilityResponse:
        part_match = _PART_RE.search(user_msg)
        model_match = _MODEL_RE.search(user_msg)

        part_number: Optional[str] = part_match.group(0).upper() if part_match else None
        model_number: Optional[str] = model_match.group(0).upper() if model_match else None

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

        messages = self._build_messages(
            history,
            f"{context}\n\nProvide a brief, helpful compatibility answer based on the above data.",
        )

        details = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages)

        return CompatibilityResponse(
            type="compatibility",
            text=status_text,
            part=product,
            model_number=model_number,
            status=status,
            details=details,
        )


# ---------------------------------------------------------------------------
# Product info agent
# ---------------------------------------------------------------------------

class ProductInfoAgent(BaseAgent):
    """Handles part lookup and product information requests."""

    async def run(
        self,
        request: ChatRequest,
        user_msg: str,
        history: List[ChatMessage],
    ) -> ProductInfoResponse:
        match = _PART_BROAD_RE.search(user_msg)
        if match:
            products = search_products(part_number=match.group(0))
            # If not in local catalog, try live lookup on PartSelect
            if not products:
                live = await lookup_part_live(match.group(0))
                if live:
                    products = [live]
        else:
            products = search_products(query=user_msg)

        products = products[:3]

        if products:
            catalog_context = "Available product information:\n" + "\n".join(
                f"- {p.part_number}: {p.name}, ${p.price or 'N/A'} — {p.description or 'See PartSelect for details'}"
                for p in products
            )
        else:
            part_num = match.group(0) if match else None
            search_link = (
                f"https://www.partselect.com/search.aspx?SearchTerm={part_num}"
                if part_num
                else "https://www.partselect.com"
            )
            catalog_context = (
                f"Part number **{part_num}** is not in our local catalog. "
                f"Tell the user it's not in local data and include this clickable link: "
                f"[Search for {part_num} on PartSelect]({search_link})"
            )

        messages = self._build_messages(
            history,
            f"{catalog_context}\n\nProvide a concise, helpful response about these parts. "
            "If no parts were found, acknowledge that and invite the customer "
            "to try a different part number or description.",
        )

        text = await chat_claude(DOMAIN_SYSTEM_PROMPT, messages)

        return ProductInfoResponse(
            type="product_info",
            text=text,
            products=[Product(**p.model_dump()) for p in products],
        )


# ---------------------------------------------------------------------------
# Troubleshooting agent
# ---------------------------------------------------------------------------

def _detect_appliance(msg: str) -> Optional[str]:
    m = msg.lower()
    if any(k in m for k in ("fridge", "refrigerator", "freezer", "ice maker")):
        return "refrigerator"
    if "dishwasher" in m:
        return "dishwasher"
    return None


class TroubleshootingAgent(BaseAgent):
    """Handles appliance symptom / troubleshooting requests."""

    async def run(
        self,
        request: ChatRequest,
        user_msg: str,
        history: List[ChatMessage],
    ) -> TroubleshootingResponse:
        appliance_type = _detect_appliance(user_msg)
        guides = await find_troubleshooting_guides(
            symptom=user_msg, appliance_type=appliance_type
        )
        logger.info("TroubleshootingAgent: guides from %s", {g.get("_source", "unknown") for g in guides})
        if len(guides) > 3:
            guides = await rerank_chunks(user_msg, guides, top_k=3)

        context_parts = []
        for g in guides[:2]:
            steps_text = "\n".join(
                f"  Step {s.get('step_number', i+1)}: "
                f"{s.get('description', s.get('text', ''))}"
                for i, s in enumerate(g.get("steps", []))
            )
            label = g.get("symptom") or g.get("text", "Guide")
            context_parts.append(f"Guide for '{label}':\n{steps_text}")

        context = "\n\n".join(context_parts) if context_parts else "No specific guide found."

        messages = self._build_messages(
            history,
            f"Context from our knowledge base:\n{context}\n\nReturn troubleshooting steps as JSON.",
        )

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
                title=s.get("title", f"Step {s.get('step_number', i + 1)}"),
                description=s.get("description", ""),
            )
            for i, s in enumerate(data.get("steps", []))
        ]
        sources = [g.get("url", "") for g in guides]

        # Collect part numbers mentioned across guide steps for part image chips
        guide_text = " ".join(
            s.get("description", "") for g in guides for s in g.get("steps", [])
        )
        part_suggestions = []
        seen: set = set()
        for m in _PART_RE.finditer(guide_text):
            pn = m.group(0).upper()
            if pn not in seen:
                seen.add(pn)
                p = get_product(pn)
                if p:
                    part_suggestions.append(Product(**p.model_dump()))

        return TroubleshootingResponse(
            type="troubleshooting",
            text=data.get("text", "Here are some troubleshooting steps:"),
            appliance_type=appliance_type,
            issue=data.get("issue"),
            steps=steps,
            sources=[s for s in sources if s],
            part_suggestions=part_suggestions[:3],
        )
