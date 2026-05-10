from __future__ import annotations

from typing import Literal, Union

from pydantic import BaseModel, Field
from typing_extensions import Annotated


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = None


class Product(BaseModel):
    part_number: str
    name: str
    price: float | None = None
    image_url: str | None = None
    url: str | None = None
    description: str | None = None


class InstallStep(BaseModel):
    step_number: int
    instruction: str
    caution: str | None = None


class TroubleshootStep(BaseModel):
    step_number: int
    description: str


class BaseResponse(BaseModel):
    type: str
    text: str


class ProductInfoResponse(BaseResponse):
    type: Literal["product_info"]
    products: list[Product]


class InstallResponse(BaseResponse):
    type: Literal["install"]
    part: Product | None = None
    steps: list[InstallStep]
    sources: list[str]


class CompatibilityResponse(BaseResponse):
    type: Literal["compatibility"]
    part: Product | None = None
    model_number: str | None = None
    status: Literal["compatible", "not_compatible", "unknown"]
    details: str | None = None


class TroubleshootingResponse(BaseResponse):
    type: Literal["troubleshooting"]
    appliance_type: Literal["refrigerator", "dishwasher"] | None = None
    issue: str | None = None
    steps: list[TroubleshootStep]
    sources: list[str]


ChatResponse = Annotated[
    Union[InstallResponse, CompatibilityResponse, TroubleshootingResponse, ProductInfoResponse],
    Field(discriminator="type"),
]
