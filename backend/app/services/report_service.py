from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from src.models import BusinessTripReport, GiftExpenseReport, RepresentativeExpenseReport
from src.report_builders import BuildResult, RepresentativeExpenseBuilder
from src.report_orchestration import (
    ReportBuildCommand,
    build_report_documents,
    representative_receipt_defaults,
    representative_single_receipt_report,
)
from src.representative_autofill import choose_profile, complete_representative_fields
from src.template_manager import TemplateManager

from ..config import Settings
from ..database_models import EmployeeRecord, GeneratedFileRecord, ReportRecord, UserRecord
from ..schemas.report import (
    BusinessTripGenerateRequest,
    GeneratedFileResponse,
    GiftGenerateRequest,
    ReportDetailResponse,
    ReportGenerateRequest,
    ReportListResponse,
    ReportSummaryResponse,
    RepresentativeGenerateRequest,
)
from .employee_service import EmployeeService


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ReportNotFoundError(LookupError):
    pass


class ReportPermissionError(PermissionError):
    pass


class ReportService:
    def __init__(self, session: Session, settings: Settings):
        self.session = session
        self.settings = settings

    def generate(self, request: ReportGenerateRequest, user: UserRecord) -> ReportDetailResponse:
        if user.role != "admin":
            if not user.employee_id:
                raise ReportPermissionError("Учётная запись не связана с сотрудником")
            if request.employee_id != user.employee_id:
                raise ReportPermissionError("Сотрудник может формировать отчёты только для себя")
        employee = EmployeeService(self.session).get_core(request.employee_id)
        report_id = str(uuid4())
        record = ReportRecord(
            id=report_id,
            report_type=request.report_type,
            status="processing",
            employee_id=request.employee_id,
            input_data=request.model_dump(mode="json"),
            build_mode=request.build_mode,
            created_by=user.id,
            warnings_data=[],
        )
        self.session.add(record)
        self.session.commit()

        output_dir = self.settings.storage_dir / "reports" / report_id
        try:
            result = self._build(request, employee, output_dir, report_id)
            record.warnings_data = list(result.warnings)
            for path in result.files:
                record.files.append(
                    GeneratedFileRecord(
                        id=str(uuid4()),
                        name=path.name,
                        stored_path=str(path),
                        mime_type=DOCX_MIME,
                        size=path.stat().st_size,
                    )
                )
            record.status = "completed"
            record.completed_at = datetime.now(timezone.utc)
            self.session.commit()
        except Exception as exc:
            record.status = "failed"
            record.error_message = str(exc)[:2000]
            record.completed_at = datetime.now(timezone.utc)
            self.session.commit()
            raise
        return self.detail(report_id, user)

    def list(self, user: UserRecord, *, limit: int = 50, offset: int = 0) -> ReportListResponse:
        base = select(ReportRecord).options(selectinload(ReportRecord.files))
        count_query = select(func.count()).select_from(ReportRecord)
        if user.role != "admin":
            base = base.where(ReportRecord.created_by == user.id)
            count_query = count_query.where(ReportRecord.created_by == user.id)
        records = self.session.scalars(
            base.order_by(ReportRecord.created_at.desc()).limit(limit).offset(offset)
        ).all()
        total = self.session.scalar(count_query) or 0
        return ReportListResponse(items=[self._summary(item) for item in records], total=total)

    def detail(self, report_id: str, user: UserRecord) -> ReportDetailResponse:
        record = self.session.scalar(
            select(ReportRecord)
            .where(ReportRecord.id == report_id)
            .options(selectinload(ReportRecord.files))
        )
        employee_can_open = (
            user.role == "employee"
            and record
            and record.created_by == user.id
            and record.employee_id == user.employee_id
        )
        if not record or (user.role != "admin" and not employee_can_open):
            raise ReportNotFoundError(report_id)
        request = self._validate_request(record.input_data)
        summary = self._summary(record)
        return ReportDetailResponse(
            **summary.model_dump(),
            input=request,
            files=[self._file_response(item) for item in record.files],
            error_message=record.error_message,
            warnings=list(record.warnings_data or []),
        )

    def file_path(self, report_id: str, file_id: str, user: UserRecord) -> tuple[Path, GeneratedFileRecord]:
        self.detail(report_id, user)
        file_record = self.session.scalar(
            select(GeneratedFileRecord).where(
                GeneratedFileRecord.id == file_id,
                GeneratedFileRecord.report_id == report_id,
            )
        )
        if not file_record:
            raise ReportNotFoundError(file_id)
        path = Path(file_record.stored_path).resolve()
        reports_root = (self.settings.storage_dir / "reports").resolve()
        if reports_root not in path.parents or not path.is_file():
            raise ReportNotFoundError(file_id)
        return path, file_record

    def zip_bytes(self, report_id: str, user: UserRecord) -> bytes:
        detail = self.detail(report_id, user)
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
            for item in detail.files:
                path, _ = self.file_path(report_id, item.id, user)
                archive.write(path, arcname=item.name)
        return buffer.getvalue()

    def _build(self, request, employee, output_dir: Path, report_id: str) -> BuildResult:
        if isinstance(request, BusinessTripGenerateRequest):
            report = BusinessTripReport(
                employee=employee,
                **request.model_dump(exclude={"report_type", "employee_id", "build_mode"}),
            )
            return build_report_documents(
                ReportBuildCommand("business_trip", report),
                self.settings.templates_dir,
                output_dir,
            )
        if isinstance(request, GiftGenerateRequest):
            report = GiftExpenseReport(
                initiator=employee,
                **request.model_dump(exclude={"report_type", "employee_id", "build_mode"}),
            )
            return build_report_documents(
                ReportBuildCommand("gifts", report),
                self.settings.templates_dir,
                output_dir,
            )

        data = request.model_dump(exclude={"report_type", "employee_id", "build_mode"})
        restaurant, place = representative_receipt_defaults(request.receipts)
        data["restaurant_name"] = data.get("restaurant_name") or restaurant
        data["place"] = data.get("place") or place
        signature = self._representative_signature(request, report_id)
        data = complete_representative_fields(data, choose_profile(signature))
        report = RepresentativeExpenseReport(initiator=employee, **data)
        if request.build_mode == "per_receipt_different_companies":
            return self._build_distinct_representative_reports(report, output_dir, report_id)
        return build_report_documents(
            ReportBuildCommand("representative_expenses", report, request.build_mode),
            self.settings.templates_dir,
            output_dir,
        )

    def _build_distinct_representative_reports(
        self,
        report: RepresentativeExpenseReport,
        output_dir: Path,
        report_id: str,
    ) -> BuildResult:
        builder = RepresentativeExpenseBuilder(TemplateManager(self.settings.templates_dir), output_dir)
        files = []
        warnings = []
        recent: list[str] = []
        for index, receipt in enumerate(report.receipts):
            single = representative_single_receipt_report(report, receipt)
            data = single.model_dump()
            data.update(
                counterparty="",
                meeting_purpose="",
                meeting_result="",
                participants_counterparty=[],
            )
            profile = choose_profile(f"{report_id}:{index}", recent)
            recent.append(profile["counterparty"])
            single = RepresentativeExpenseReport(**complete_representative_fields(data, profile))
            result = builder.build(single)
            files.extend(result.files)
            warnings.extend(result.warnings)
        return BuildResult(files=files, warnings=warnings)

    @staticmethod
    def _representative_signature(request: RepresentativeGenerateRequest, report_id: str) -> str:
        receipt_parts = [
            f"{item.file_name}:{item.date or ''}:{item.amount}:{item.seller or ''}:{item.address or ''}"
            for item in request.receipts
        ]
        return "|".join([report_id, request.employee_id, str(request.event_date), *receipt_parts])

    def _summary(self, record: ReportRecord) -> ReportSummaryResponse:
        employee = self.session.get(EmployeeRecord, record.employee_id) if record.employee_id else None
        receipts = record.input_data.get("receipts", [])
        total = sum((Decimal(str(item.get("amount", 0))) for item in receipts), Decimal("0"))
        return ReportSummaryResponse(
            id=record.id,
            report_type=record.report_type,
            status=record.status,
            employee_id=record.employee_id,
            employee_name=employee.full_name if employee else None,
            build_mode=record.build_mode,
            total_amount=total,
            created_at=record.created_at,
            completed_at=record.completed_at,
            files_count=len(record.files),
        )

    @staticmethod
    def _validate_request(data: dict[str, object]):
        report_type = data.get("report_type")
        schema = {
            "business_trip": BusinessTripGenerateRequest,
            "representative_expenses": RepresentativeGenerateRequest,
            "gifts": GiftGenerateRequest,
        }.get(str(report_type))
        if not schema:
            raise ValueError("Неизвестный тип сохраненного отчета")
        return schema.model_validate(data)

    @staticmethod
    def _file_response(record: GeneratedFileRecord) -> GeneratedFileResponse:
        return GeneratedFileResponse(
            id=record.id,
            name=record.name,
            mime_type=record.mime_type,
            size=record.size,
            download_url=f"/api/reports/{record.report_id}/files/{record.id}",
        )
