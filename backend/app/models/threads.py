from __future__ import annotations

from pydantic import BaseModel


class Thread(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str
