from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.core.security import add_user, create_token, get_user_by_username
from app.models.auth import AuthResponse, LoginRequest, SignupRequest, User, UserPublic

router = APIRouter()

_DATA_DIR = Path(__file__).parent.parent / "data"


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest) -> AuthResponse:
    user = get_user_by_username(body.username)
    if user is None or user.password != body.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_token(user.id)
    return AuthResponse(token=token, user=UserPublic(id=user.id, username=user.username))


@router.post("/signup", response_model=AuthResponse)
async def signup(body: SignupRequest) -> AuthResponse:
    if get_user_by_username(body.username) is not None:
        raise HTTPException(status_code=400, detail="Username already exists")

    user_id = f"user_{uuid4().hex[:8]}"
    from datetime import datetime, timezone
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new_user = User(
        id=user_id,
        username=body.username,
        password=body.password,
        created_at=created_at,
    )
    add_user(new_user)

    # Append to users.json
    users_path = _DATA_DIR / "users.json"
    try:
        existing = json.loads(users_path.read_text(encoding="utf-8"))
        existing.append(new_user.model_dump())
        users_path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass  # Best-effort persistence; user is already in memory

    token = create_token(new_user.id)
    return AuthResponse(
        token=token,
        user=UserPublic(id=new_user.id, username=new_user.username),
    )
