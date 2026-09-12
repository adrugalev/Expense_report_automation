from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..database_models import UserRecord
from ..dependencies import require_roles
from ..schemas.dashboard import DashboardResponse
from ..services.dashboard_service import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def dashboard(
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    user: UserRecord = Depends(require_roles("admin")),
) -> DashboardResponse:
    return DashboardService(session, settings).get(user)
