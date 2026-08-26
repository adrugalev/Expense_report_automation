from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class EmployeeAccountResponse(BaseModel):
    employee_id: str
    full_name: str
    email: EmailStr | None
    has_account: bool
    is_active: bool
    role: Literal["admin", "employee"] | None


class EmployeePasswordUpdate(BaseModel):
    password: str = Field(min_length=8, max_length=128)
