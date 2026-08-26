from __future__ import annotations

from pydantic import BaseModel


class VersionHistoryResponse(BaseModel):
    revision: int
    date: str
    changes: list[str]


class AppMetaResponse(BaseModel):
    version: str
    version_date: str
    version_revision: int
    history: list[VersionHistoryResponse]
