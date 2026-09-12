from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import Settings
from ..database_models import EmployeeRecord, ReportRecord, UserRecord
from ..schemas.dashboard import DashboardResponse
from .report_service import ReportService


class DashboardService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings

    def get(self, user: UserRecord) -> DashboardResponse:
        report_filter = ReportRecord.created_by == user.id if user.role != "admin" else None

        def report_count(status: str | None = None) -> int:
            query = select(func.count()).select_from(ReportRecord)
            if report_filter is not None:
                query = query.where(report_filter)
            if status:
                query = query.where(ReportRecord.status == status)
            return self.session.scalar(query) or 0

        recent = ReportService(self.session, self.settings).list(user, limit=5).items
        employees_total = self.session.scalar(select(func.count()).select_from(EmployeeRecord)) or 0
        return DashboardResponse(
            reports_total=report_count(),
            reports_completed=report_count("completed"),
            reports_failed=report_count("failed"),
            employees_total=employees_total,
            recent_reports=recent,
        )
