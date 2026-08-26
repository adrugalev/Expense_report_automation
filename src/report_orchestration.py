from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from .models import BusinessTripReport, GiftExpenseReport, Receipt, RepresentativeExpenseReport
from .report_builders import (
    BuildResult,
    BusinessTripBuilder,
    GiftExpenseBuilder,
    RepresentativeExpenseBuilder,
)
from .template_manager import TemplateManager


ReportType = Literal["business_trip", "representative_expenses", "gifts"]
BuildMode = Literal["single", "per_receipt", "per_receipt_different_companies"]


@dataclass(frozen=True)
class ReportBuildCommand:
    report_type: ReportType
    report: BusinessTripReport | RepresentativeExpenseReport | GiftExpenseReport
    build_mode: BuildMode = "single"


def build_report_documents(
    command: ReportBuildCommand,
    templates_dir: Path,
    output_dir: Path,
) -> BuildResult:
    """Build documents for both web and legacy callers without UI dependencies."""

    manager = TemplateManager(templates_dir)
    if command.report_type == "business_trip":
        if not isinstance(command.report, BusinessTripReport):
            raise TypeError("Для командировки передана неверная модель отчета")
        return BusinessTripBuilder(manager, output_dir).build(command.report)
    if command.report_type == "gifts":
        if not isinstance(command.report, GiftExpenseReport):
            raise TypeError("Для подарков передана неверная модель отчета")
        return GiftExpenseBuilder(manager, output_dir).build(command.report)
    if not isinstance(command.report, RepresentativeExpenseReport):
        raise TypeError("Для представительских расходов передана неверная модель отчета")

    builder = RepresentativeExpenseBuilder(manager, output_dir)
    if command.build_mode == "per_receipt":
        return _build_representative_per_receipt(builder, command.report)
    if command.build_mode == "per_receipt_different_companies":
        raise ValueError("Для режима разных компаний отчеты должны быть подготовлены service layer")
    return builder.build(command.report)


def representative_receipt_defaults(receipts: list[Receipt]) -> tuple[str, str]:
    for receipt in receipts:
        if receipt.expense_type == "ресторан" or receipt.seller or receipt.address:
            return receipt.seller or "", receipt.address or ""
    return "", ""


def representative_single_receipt_report(
    report: RepresentativeExpenseReport,
    receipt: Receipt,
) -> RepresentativeExpenseReport:
    return report.model_copy(
        update={
            "receipts": [receipt],
            "restaurant_name": receipt.seller or "",
            "place": receipt.address or "",
            "event_date": receipt.date or report.event_date,
        }
    )


def _build_representative_per_receipt(
    builder: RepresentativeExpenseBuilder,
    report: RepresentativeExpenseReport,
) -> BuildResult:
    files = []
    warnings = []
    for receipt in report.receipts:
        result = builder.build(representative_single_receipt_report(report, receipt))
        files.extend(result.files)
        warnings.extend(result.warnings)
    return BuildResult(files=files, warnings=warnings)
