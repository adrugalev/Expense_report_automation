from __future__ import annotations

from io import BytesIO

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from src.representative_autofill import choose_profile, complete_representative_fields

from ..config import Settings, get_settings
from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import get_current_user, require_roles
from ..schemas.report import (
    ReportDetailResponse,
    ReportGenerateRequest,
    ReportListResponse,
    ReportTypeResponse,
    RepresentativeSuggestionRequest,
    RepresentativeSuggestionResponse,
)
from ..services.report_service import ReportNotFoundError, ReportPermissionError, ReportService


router = APIRouter(prefix="/reports", tags=["reports"])

REPORT_TYPES = [
    ReportTypeResponse(
        id="business_trip",
        name="Командировка",
        description="Компенсация поездок на такси в период командировки",
        accepted_expense_type="такси",
    ),
    ReportTypeResponse(
        id="representative_expenses",
        name="Представительские расходы",
        description="Деловая встреча, участники и подтверждающие ресторанные чеки",
        accepted_expense_type="ресторан",
    ),
    ReportTypeResponse(
        id="gifts",
        name="Подарки",
        description="Служебная записка на приобретение подарочной продукции",
        accepted_expense_type="подарки",
    ),
]


@router.get("/types", response_model=list[ReportTypeResponse])
def report_types(_user: UserRecord = Depends(get_current_user)) -> list[ReportTypeResponse]:
    return REPORT_TYPES


@router.post("/suggestions/representative", response_model=RepresentativeSuggestionResponse)
def representative_suggestion(
    data: RepresentativeSuggestionRequest,
    _user: UserRecord = Depends(require_roles("admin", "employee")),
) -> RepresentativeSuggestionResponse:
    profile = choose_profile(data.signature, data.recent_counterparties)
    completed = complete_representative_fields(
        {
            "counterparty": "",
            "meeting_purpose": "",
            "meeting_result": "",
            "participants_counterparty": [],
        },
        profile,
    )
    return RepresentativeSuggestionResponse(**completed)


@router.post("/generate", response_model=ReportDetailResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    request: ReportGenerateRequest = Body(..., discriminator="report_type"),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin", "employee")),
) -> ReportDetailResponse:
    try:
        return await run_in_threadpool(ReportService(session, settings).generate, request, user)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сотрудник не найден") from exc
    except ReportPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("", response_model=ReportListResponse)
def list_reports(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin")),
) -> ReportListResponse:
    return ReportService(session, settings).list(user, limit=limit, offset=offset)


@router.get("/{report_id}", response_model=ReportDetailResponse)
def report_detail(
    report_id: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(get_current_user),
) -> ReportDetailResponse:
    try:
        return ReportService(session, settings).detail(report_id, user)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчет не найден") from exc


@router.get("/{report_id}/files/{file_id}", response_class=FileResponse)
def download_file(
    report_id: str,
    file_id: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(get_current_user),
) -> FileResponse:
    try:
        path, record = ReportService(session, settings).file_path(report_id, file_id, user)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден") from exc
    return FileResponse(path, media_type=record.mime_type, filename=record.name)


@router.get("/{report_id}/files.zip")
def download_zip(
    report_id: str,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(get_current_user),
) -> StreamingResponse:
    try:
        payload = ReportService(session, settings).zip_bytes(report_id, user)
    except ReportNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отчет не найден") from exc
    headers = {"Content-Disposition": 'attachment; filename="report_documents.zip"'}
    return StreamingResponse(BytesIO(payload), media_type="application/zip", headers=headers)
