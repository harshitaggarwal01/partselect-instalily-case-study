from __future__ import annotations

from app.models.schemas import ChatRequest, ChatResponse, ProductInfoResponse
from app.services.handlers.compatibility import handle_compatibility
from app.services.handlers.install import handle_install
from app.services.handlers.product_info import handle_product_info
from app.services.handlers.troubleshooting import handle_troubleshooting
from app.services.intent_router import detect_intent


async def run_agent(request: ChatRequest) -> ChatResponse:
    user_msg = request.messages[-1].content
    intent = await detect_intent(user_msg)

    if intent == "install":
        return await handle_install(request, user_msg)
    elif intent == "compatibility":
        return await handle_compatibility(request, user_msg)
    elif intent == "product_info":
        return await handle_product_info(request, user_msg)
    elif intent == "troubleshooting":
        return await handle_troubleshooting(request, user_msg)
    else:
        return ProductInfoResponse(
            type="product_info",
            text=(
                "I specialize in refrigerator and dishwasher parts only. "
                "Try asking about a specific part number, how to install a part, "
                "whether a part fits your model, or how to fix a common issue."
            ),
            products=[],
        )
