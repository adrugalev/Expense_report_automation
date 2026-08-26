from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from src.models import Receipt


class UploadResponse(BaseModel):
    id: str
    original_name: str
    mime_type: str
    size: int
    receipt: Receipt
    created_at: datetime
