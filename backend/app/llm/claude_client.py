from __future__ import annotations

import json
import re

import anthropic

from app.core.config import settings

DOMAIN_SYSTEM_PROMPT = """You are a helpful customer support agent for PartSelect, an online retailer \
specializing in appliance parts. You assist customers exclusively with refrigerator and dishwasher parts, \
installation instructions, compatibility questions, and troubleshooting. \
Never answer questions outside this domain (e.g., washing machines, ovens, HVAC, or unrelated topics). \
If a customer asks about something outside refrigerators or dishwashers, politely decline and redirect \
them to refrigerator or dishwasher part questions. Always be concise, accurate, and helpful."""

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


class ExternalAPIError(Exception):
    pass


async def chat_claude(
    system_prompt: str,
    messages: list[dict],
    max_tokens: int = 1024,
) -> str:
    try:
        client = _get_client()
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=max_tokens,
            system=system_prompt,
            messages=messages,
        )
        return response.content[0].text
    except anthropic.APIError as exc:
        raise ExternalAPIError(str(exc)) from exc


async def chat_claude_json(
    system_prompt: str,
    messages: list[dict],
    json_schema_description: str,
    max_tokens: int = 1024,
) -> dict:
    augmented_system = (
        system_prompt
        + f"\n\nYou MUST respond with a valid JSON object only — no prose before or after. "
        f"The JSON must match this schema:\n{json_schema_description}"
    )
    raw = await chat_claude(augmented_system, messages, max_tokens=max_tokens)
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"text": raw, "parse_error": True}
