from __future__ import annotations

import time

from fastapi import APIRouter

from app.core.logging import log_interaction
from app.llm.claude_client import ExternalAPIError
from app.models.schemas import ChatRequest, ChatResponse, TroubleshootingResponse
from app.services.agent import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    t0 = time.monotonic()
    try:
        response = await run_agent(request)
        latency_ms = (time.monotonic() - t0) * 1000
        log_interaction(
            intent=response.type,
            response_type=response.type,
            latency_ms=latency_ms,
            parse_error=getattr(response, "_parse_error", False),
        )
        return response
    except ExternalAPIError:
        latency_ms = (time.monotonic() - t0) * 1000
        log_interaction("unknown", "error", latency_ms)
        return TroubleshootingResponse(
            type="troubleshooting",
            text=(
                "I'm having trouble reaching my knowledge sources right now. "
                "Please try again in a moment."
            ),
            appliance_type=None,
            issue=None,
            steps=[],
            sources=[],
        )
