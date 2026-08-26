from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import require_roles
from ..schemas.upload import UploadResponse
from ..services.upload_service import UploadService, UploadValidationError


router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("/receipts", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "user")),
) -> UploadResponse:
    payload = await file.read(settings.max_upload_size + 1)
    try:
        return await run_in_threadpool(
            UploadService(session, settings).create_receipt_upload,
            original_name=file.filename or "receipt",
            content_type=file.content_type,
            payload=payload,
            user=user,
        )
    except UploadValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "user")),
) -> None:
    try:
        UploadService(session, settings).delete(upload_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден") from exc
