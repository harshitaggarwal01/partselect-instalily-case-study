from fastapi import APIRouter

from app.llm.claude_client import ExternalAPIError
from app.models.schemas import ChatRequest, ChatResponse, TroubleshootingResponse
from app.services.agent import run_agent

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    try:
        return await run_agent(request)
    except ExternalAPIError:
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
