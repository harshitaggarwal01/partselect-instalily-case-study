from __future__ import annotations

from pydantic import BaseModel


class User(BaseModel):
    id: str
    username: str
    password: str
    created_at: str


class UserPublic(BaseModel):
    id: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class SignupRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: UserPublic
