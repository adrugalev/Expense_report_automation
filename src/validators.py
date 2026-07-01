from __future__ import annotations

from datetime import date
from decimal import Decimal

from .models import BusinessTripReport, Receipt


def validate_receipt_amount(receipt: Receipt) -> None:
    if receipt.amount <= Decimal("0"):
        raise ValueError("Сумма чека должна быть больше 0")


def validate_receipt_not_after_report(receipt: Receipt, report_date: date) -> None:
    if receipt.date and receipt.date > report_date:
        raise ValueError("Дата чека не может быть позже даты составления отчёта")


def validate_trip_receipts_period(report: BusinessTripReport, tolerance_days: int = 1) -> None:
    for receipt in report.receipts:
        if receipt.date is None:
            continue
        if (report.trip_start_date - receipt.date).days > tolerance_days:
            raise ValueError("Дата чека слишком рано для периода командировки")
        if (receipt.date - report.trip_end_date).days > tolerance_days:
            raise ValueError("Дата чека слишком поздно для периода командировки")


def total_receipts_amount(receipts: list[Receipt]) -> Decimal:
    return sum((receipt.amount for receipt in receipts), Decimal("0"))

