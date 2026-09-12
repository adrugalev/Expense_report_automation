from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from src.receipt_parser import ProgressCallback, parse_receipt_path
from src.utils import slugify_file_part

from ..config import Settings
from ..database_models import UploadRecord, UserRecord
from ..schemas.upload import UploadResponse


class UploadValidationError(ValueError):
    pass


ALLOWED_FILE_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def detect_file_type(payload: bytes) -> str | None:
    if payload.startswith(b"%PDF-"):
        return "application/pdf"
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if payload.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


class UploadService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings

    def create_receipt_upload(
        self,
        *,
        original_name: str,
        content_type: str | None,
        payload: bytes,
        user: UserRecord,
        progress_callback: ProgressCallback | None = None,
    ) -> UploadResponse:
        if progress_callback:
            progress_callback(3, "Проверка файла")
        safe_original = Path(original_name).name
        suffix = Path(safe_original).suffix.lower()
        expected_type = ALLOWED_FILE_TYPES.get(suffix)
        detected_type = detect_file_type(payload)
        if not expected_type:
            raise UploadValidationError("Поддерживаются только PDF, PNG, JPG и JPEG")
        if len(payload) > self.settings.max_upload_size:
            limit_mb = self.settings.max_upload_size // (1024 * 1024)
            raise UploadValidationError(f"Размер файла превышает {limit_mb} МБ")
        if not payload:
            raise UploadValidationError("Загружен пустой файл")
        if detected_type != expected_type:
            raise UploadValidationError("Содержимое файла не соответствует его расширению")
        if content_type and content_type not in {expected_type, "application/octet-stream"}:
            raise UploadValidationError("MIME-тип файла не соответствует допустимому формату")

        upload_id = str(uuid4())
        user_dir = self.settings.storage_dir / "uploads" / user.id
        user_dir.mkdir(parents=True, exist_ok=True)
        safe_stem = slugify_file_part(Path(safe_original).stem, "receipt")[:80]
        stored_path = user_dir / f"{upload_id}_{safe_stem}{suffix}"
        stored_path.write_bytes(payload)
        if progress_callback:
            progress_callback(8, "Файл сохранён")
        try:
            receipt = parse_receipt_path(
                stored_path,
                file_name=safe_original,
                progress_callback=progress_callback,
            )
        except Exception:
            stored_path.unlink(missing_ok=True)
            raise

        record = UploadRecord(
            id=upload_id,
            original_name=safe_original,
            stored_path=str(stored_path),
            mime_type=detected_type,
            size=len(payload),
            receipt_data=receipt.model_dump(mode="json"),
            created_by=user.id,
        )
        self.session.add(record)
        self.session.commit()
        if progress_callback:
            progress_callback(100, "Готово")
        return UploadResponse(
            id=record.id,
            original_name=record.original_name,
            mime_type=record.mime_type,
            size=record.size,
            receipt=receipt,
            created_at=record.created_at,
        )

    def delete(self, upload_id: str, user: UserRecord) -> None:
        record = self.session.get(UploadRecord, upload_id)
        if not record or (record.created_by != user.id and user.role != "admin"):
            raise LookupError(upload_id)
        Path(record.stored_path).unlink(missing_ok=True)
        self.session.delete(record)
        self.session.commit()
