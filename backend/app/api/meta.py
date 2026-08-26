from __future__ import annotations

from fastapi import APIRouter

from src.version import APP_VERSION_DATE, APP_VERSION_REVISION, app_version_history, app_version_label

from ..schemas.meta import AppMetaResponse, VersionHistoryResponse


router = APIRouter(tags=["meta"])


@router.get("/meta", response_model=AppMetaResponse)
def meta() -> AppMetaResponse:
    return AppMetaResponse(
        version=app_version_label(),
        version_date=APP_VERSION_DATE,
        version_revision=APP_VERSION_REVISION,
        history=[
            VersionHistoryResponse(revision=item.revision, date=item.date, changes=list(item.changes))
            for item in app_version_history()
        ],
    )
