from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


Role = Literal["admin", "employee"]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class ChangeOwnPasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: Role
    employee_id: str | None


class SessionResponse(BaseModel):
    user: UserResponse
    expires_in: int
