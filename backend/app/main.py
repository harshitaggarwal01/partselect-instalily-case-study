from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.cart import router as cart_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.threads import router as threads_router
from app.core.config import settings
from app.core.security import load_users
from app.models.auth import User

DATA_DIR = Path(__file__).parent / "data"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load users on startup
    users_data = json.loads((DATA_DIR / "users.json").read_text(encoding="utf-8"))
    load_users([User(**u) for u in users_data])
    yield


app = FastAPI(title="PartSelect Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router, prefix="/api")
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api/auth")
app.include_router(threads_router, prefix="/api/threads")
app.include_router(cart_router, prefix="/api/cart")
