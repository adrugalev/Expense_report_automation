from datetime import date
from decimal import Decimal

import pytest

from src.models import BusinessTripReport, Employee, Receipt
from src.validators import total_receipts_amount


def employee() -> Employee:
    return Employee(full_name="Иванов Иван", position="Менеджер", department="Отдел")


def test_receipt_date_after_report_is_invalid():
    with pytest.raises(ValueError, match="Дата чека"):
        BusinessTripReport(
            employee=employee(),
            trip_city="Москва",
            trip_start_date=date(2026, 6, 20),
            trip_end_date=date(2026, 6, 25),
            purpose="Встреча",
            receipts=[Receipt(file_name="check.jpg", date=date(2026, 6, 30), amount=Decimal("100"), expense_type="такси")],
            report_date=date(2026, 6, 26),
        )


def test_trip_receipt_outside_period_is_invalid():
    with pytest.raises(ValueError, match="период командировки"):
        BusinessTripReport(
            employee=employee(),
            trip_city="Москва",
            trip_start_date=date(2026, 6, 20),
            trip_end_date=date(2026, 6, 25),
            purpose="Встреча",
            receipts=[Receipt(file_name="check.jpg", date=date(2026, 6, 10), amount=Decimal("100"), expense_type="такси")],
            report_date=date(2026, 6, 26),
        )


def test_total_receipts_amount():
    receipts = [
        Receipt(file_name="1.jpg", amount=Decimal("100.50")),
        Receipt(file_name="2.jpg", amount=Decimal("99.50")),
    ]
    assert total_receipts_amount(receipts) == Decimal("200.00")

