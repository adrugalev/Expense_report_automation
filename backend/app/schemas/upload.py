from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from src.models import Receipt


class UploadResponse(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size: int
    receipt: Receipt
    created_at: datetime


class ReceiptJobStartResponse(BaseModel):
    job_id: str


class ReceiptJobStatusResponse(BaseModel):
    job_id: str
    status: Literal["queued", "processing", "completed", "failed"]
    progress: int
    stage: str
    result: UploadResponse | None = None
    error: str | None = None
