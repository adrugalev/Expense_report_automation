from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import SessionLocal, get_db
from ..database_models import UserRecord
from ..dependencies import require_roles
from ..schemas.upload import ReceiptJobStartResponse, ReceiptJobStatusResponse, UploadResponse
from ..services.upload_service import UploadService, UploadValidationError


router = APIRouter(prefix="/uploads", tags=["uploads"])
logger = logging.getLogger(__name__)


@dataclass
class _ReceiptJob:
    user_id: str
    status: str = "queued"
    progress: int = 1
    stage: str = "Файл поставлен в очередь"
    result: UploadResponse | None = None
    error: str | None = None
    updated_at: float = 0.0


_receipt_jobs: dict[str, _ReceiptJob] = {}
_receipt_jobs_lock = threading.Lock()
_STAGE_PROGRESS_LIMITS = {
    "Проверка файла": 7,
    "Файл сохранён": 11,
    "Поиск QR-кода": 27,
    "Подготовка изображения": 34,
    "Подготовка страниц PDF": 34,
    "Распознавание текста": 75,
    "Извлечение реквизитов": 81,
    "Дополнительная проверка суммы и ФД": 91,
    "Проверка распознанных данных": 95,
    "Подготовка результата": 99,
}


def _update_receipt_job(job_id: str, **changes) -> None:
    with _receipt_jobs_lock:
        job = _receipt_jobs.get(job_id)
        if not job:
            return
        for field, value in changes.items():
            setattr(job, field, value)
        job.updated_at = time.monotonic()


def _cleanup_receipt_jobs() -> None:
    threshold = time.monotonic() - 3600
    with _receipt_jobs_lock:
        expired = [
            job_id
            for job_id, job in _receipt_jobs.items()
            if job.status in {"completed", "failed"} and job.updated_at < threshold
        ]
        for job_id in expired:
            _receipt_jobs.pop(job_id, None)


def _run_receipt_job(
    job_id: str,
    *,
    original_name: str,
    content_type: str | None,
    payload: bytes,
    user_id: str,
    settings: Settings,
) -> None:
    _update_receipt_job(job_id, status="processing", progress=2, stage="Начало обработки")
    activity_stop = threading.Event()

    def advance_active_stage() -> None:
        while not activity_stop.wait(0.5):
            with _receipt_jobs_lock:
                job = _receipt_jobs.get(job_id)
                if not job or job.status != "processing":
                    return
                limit = _STAGE_PROGRESS_LIMITS.get(job.stage, job.progress)
                if job.progress < limit:
                    job.progress += 1
                    job.updated_at = time.monotonic()

    activity_thread = threading.Thread(target=advance_active_stage, daemon=True)
    activity_thread.start()

    def report_progress(percent: int, stage: str) -> None:
        _update_receipt_job(job_id, progress=max(0, min(100, percent)), stage=stage)

    try:
        with SessionLocal() as session:
            user = session.get(UserRecord, user_id)
            if not user or not user.is_active:
                raise UploadValidationError("Пользователь больше не доступен")
            result = UploadService(session, settings).create_receipt_upload(
                original_name=original_name,
                content_type=content_type,
                payload=payload,
                user=user,
                progress_callback=report_progress,
            )
        _update_receipt_job(
            job_id,
            status="completed",
            progress=100,
            stage="Готово",
            result=result,
        )
    except UploadValidationError as exc:
        _update_receipt_job(job_id, status="failed", stage="Ошибка", error=str(exc))
    except Exception:
        logger.exception("Receipt recognition job %s failed", job_id)
        _update_receipt_job(
            job_id,
            status="failed",
            stage="Ошибка",
            error="Не удалось распознать чек",
        )
    finally:
        activity_stop.set()
        activity_thread.join(timeout=1)


@router.post("/receipts", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "employee")),
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


@router.post(
    "/receipts/jobs",
    response_model=ReceiptJobStartResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_receipt_job(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "employee")),
) -> ReceiptJobStartResponse:
    payload = await file.read(settings.max_upload_size + 1)
    job_id = str(uuid4())
    _cleanup_receipt_jobs()
    with _receipt_jobs_lock:
        _receipt_jobs[job_id] = _ReceiptJob(user_id=user.id, updated_at=time.monotonic())
    worker = threading.Thread(
        target=_run_receipt_job,
        kwargs={
            "job_id": job_id,
            "original_name": file.filename or "receipt",
            "content_type": file.content_type,
            "payload": payload,
            "user_id": user.id,
            "settings": settings,
        },
        daemon=True,
    )
    worker.start()
    return ReceiptJobStartResponse(job_id=job_id)


@router.get("/receipts/jobs/{job_id}", response_model=ReceiptJobStatusResponse)
def get_receipt_job(
    job_id: str,
    user: UserRecord = Depends(require_roles("admin", "employee")),
) -> ReceiptJobStatusResponse:
    with _receipt_jobs_lock:
        job = _receipt_jobs.get(job_id)
        if not job or (job.user_id != user.id and user.role != "admin"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
        return ReceiptJobStatusResponse(
            job_id=job_id,
            status=job.status,
            progress=job.progress,
            stage=job.stage,
            result=job.result,
            error=job.error,
        )


@router.delete("/{upload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_upload(
    upload_id: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "employee")),
) -> None:
    try:
        UploadService(session, settings).delete(upload_id, user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден") from exc
