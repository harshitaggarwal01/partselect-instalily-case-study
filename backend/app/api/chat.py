from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException, Request

from app.core.logging import log_interaction
from app.core.security import get_current_user
from app.llm.claude_client import ExternalAPIError
from app.models.schemas import ChatRequest, ChatResponse, TroubleshootingResponse
from app.services.agent import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(body: ChatRequest, request: Request) -> ChatResponse:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")

    t0 = time.monotonic()
    try:
        response = await run_agent(body, user_id=user.id)
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
