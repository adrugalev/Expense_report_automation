from __future__ import annotations

from pydantic import BaseModel

from .report import ReportSummaryResponse


class DashboardResponse(BaseModel):
    reports_total: int
    reports_completed: int
    reports_failed: int
    employees_total: int
    recent_reports: list[ReportSummaryResponse]
