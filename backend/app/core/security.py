from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import Optional

from fastapi import Request

from app.models.auth import User

SECRET_KEY = "partselect_demo_secret_2026"

# In-memory user cache loaded at startup
_users: dict[str, User] = {}


def load_users(users: list[User]) -> None:
    for u in users:
        _users[u.id] = u


def get_user_by_username(username: str) -> Optional[User]:
    return next((u for u in _users.values() if u.username == username), None)


def get_user_by_id(user_id: str) -> Optional[User]:
    return _users.get(user_id)


def add_user(user: User) -> None:
    _users[user.id] = user


def get_all_users() -> list[User]:
    return list(_users.values())


def create_token(user_id: str) -> str:
    payload = f"{user_id}:{int(time.time())}"
    payload_b64 = base64.b64encode(payload.encode()).decode()
    sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def parse_token(token: str) -> Optional[str]:
    try:
        payload_b64, sig = token.rsplit(".", 1)
        expected = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = base64.b64decode(payload_b64.encode()).decode()
        user_id = payload.split(":")[0]
        return user_id
    except Exception:
        return None


def get_current_user(request: Request) -> Optional[User]:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    user_id = parse_token(token)
    if not user_id:
        return None
    return get_user_by_id(user_id)
