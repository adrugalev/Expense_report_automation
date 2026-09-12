from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class EmployeeBase(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    short_name: str | None = Field(default=None, max_length=255)
    position: str = Field(min_length=2, max_length=255)
    department: str = Field(default="", max_length=255)
    company: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    email: EmailStr | None = None
    manager_name: str | None = Field(default=None, max_length=255)
    manager_position: str | None = Field(default=None, max_length=255)
    default_signatory_name: str | None = Field(default=None, max_length=255)
    default_signatory_position: str | None = Field(default=None, max_length=255)

    @field_validator("full_name", "position")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return value.strip()


class EmployeeCreate(EmployeeBase):
    id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9_-]+$", max_length=100)


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    id: str
