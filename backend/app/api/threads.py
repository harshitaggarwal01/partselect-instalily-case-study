from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.security import get_current_user
from app.models.schemas import ChatMessage
from app.models.threads import Thread
from app.services.thread_store import thread_store

router = APIRouter()


class CreateThreadBody(BaseModel):
    title: Optional[str] = None


@router.get("/")
async def list_threads(request: Request) -> list[Thread]:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return await thread_store.list_threads(user.id)


@router.post("/")
async def create_thread(body: CreateThreadBody, request: Request) -> Thread:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    title = body.title or "New Conversation"
    return await thread_store.create_thread(user_id=user.id, title=title)


@router.get("/{thread_id}")
async def get_thread(thread_id: str, request: Request) -> dict:
    user = get_current_user(request)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    thread = await thread_store.get_thread(thread_id, user.id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = await thread_store.get_recent_messages(thread_id, limit=20)
    return {"thread": thread, "messages": messages}
