from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from app.models.schemas import ChatMessage
from app.models.threads import Thread

_DATA_PATH = Path(__file__).parent.parent / "data" / "threads.json"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_data() -> dict:
    try:
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"threads": [], "messages": []}


def _save_data(data: dict) -> None:
    _DATA_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


class ThreadStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._data: dict = _load_data()

    async def list_threads(self, user_id: str) -> list[Thread]:
        threads = [
            Thread(**t)
            for t in self._data.get("threads", [])
            if t.get("user_id") == user_id
        ]
        threads.sort(key=lambda t: t.updated_at, reverse=True)
        return threads

    async def get_thread(self, thread_id: str, user_id: str) -> Optional[Thread]:
        for t in self._data.get("threads", []):
            if t.get("id") == thread_id and t.get("user_id") == user_id:
                return Thread(**t)
        return None

    async def create_thread(
        self, user_id: str, title: str = "New Conversation"
    ) -> Thread:
        now = _utcnow_iso()
        thread = Thread(
            id=f"thr_{uuid4().hex[:8]}",
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now,
        )
        async with self._lock:
            self._data.setdefault("threads", []).append(thread.model_dump())
            _save_data(self._data)
        return thread

    async def get_recent_messages(
        self, thread_id: str, limit: int = 20
    ) -> list[ChatMessage]:
        messages = [
            ChatMessage(**m)
            for m in self._data.get("messages", [])
            if m.get("thread_id") == thread_id
        ]
        return messages[-limit:]

    async def append_messages(
        self, thread_id: str, messages: list[ChatMessage]
    ) -> None:
        async with self._lock:
            self._data.setdefault("messages", [])
            for msg in messages:
                entry = msg.model_dump()
                entry["thread_id"] = thread_id
                self._data["messages"].append(entry)

            # Update thread updated_at
            now = _utcnow_iso()
            for t in self._data.get("threads", []):
                if t.get("id") == thread_id:
                    t["updated_at"] = now
                    break

            _save_data(self._data)

    async def update_messages_for_thread(
        self, thread_id: str, messages: list[ChatMessage]
    ) -> None:
        async with self._lock:
            # Remove all existing messages for this thread
            self._data["messages"] = [
                m
                for m in self._data.get("messages", [])
                if m.get("thread_id") != thread_id
            ]
            # Append the new message list
            for msg in messages:
                entry = msg.model_dump()
                entry["thread_id"] = thread_id
                self._data["messages"].append(entry)

            # Update thread updated_at
            now = _utcnow_iso()
            for t in self._data.get("threads", []):
                if t.get("id") == thread_id:
                    t["updated_at"] = now
                    break

            _save_data(self._data)


    async def update_title(self, thread_id: str, title: str) -> None:
        async with self._lock:
            for t in self._data.get("threads", []):
                if t.get("id") == thread_id:
                    t["title"] = title
                    break
            _save_data(self._data)


thread_store = ThreadStore()
