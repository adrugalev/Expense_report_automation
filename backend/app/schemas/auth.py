from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


Role = Literal["admin", "user", "viewer"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role


class SessionResponse(BaseModel):
    user: UserResponse
    expires_in: int
