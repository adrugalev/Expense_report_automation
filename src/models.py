from __future__ import annotations

from datetime import date as Date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ExpenseType = Literal["такси", "ресторан", "подарки", "прочее"]


class Employee(BaseModel):
    id: str | None = None
    full_name: str
    short_name: str | None = None
    position: str
    department: str = ""
    company: str | None = None
    phone: str | None = None
    email: str | None = None
    manager_name: str | None = None
    manager_position: str | None = None
    default_signatory_name: str | None = None
    default_signatory_position: str | None = None

    @field_validator("full_name", "position")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Поле обязательно для заполнения")
        return value

    @field_validator("department", mode="before")
    @classmethod
    def optional_department(cls, value: object) -> str:
        return "" if value is None else str(value).strip()


class Receipt(BaseModel):
    file_name: str
    date: Date | None = None
    seller: str | None = None
    address: str | None = None
    inn: str | None = None
    amount: Decimal = Field(gt=0)
    expense_type: ExpenseType = "прочее"
    comment: str | None = None
    route: str | None = None
    fiscal_number: str | None = None
    check_number: str | None = None
    shift_number: str | None = None
    kkt_number: str | None = None
    fiscal_document_number: str | None = None
    fiscal_drive_number: str | None = None
    fiscal_sign: str | None = None
    payment_type: str | None = None
    qr_raw: str | None = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("amount", mode="before")
    @classmethod
    def normalize_amount(cls, value: object) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            value = value.replace(" ", "").replace(",", ".").replace("₽", "")
        return Decimal(str(value))


class BaseReport(BaseModel):
    receipts: list[Receipt] = Field(default_factory=list)
    report_date: Date

    @model_validator(mode="after")
    def validate_receipts_before_report(self) -> "BaseReport":
        for receipt in self.receipts:
            if receipt.date and receipt.date > self.report_date:
                raise ValueError("Дата чека не может быть позже даты составления отчёта")
        return self

    @property
    def total_amount(self) -> Decimal:
        return sum((receipt.amount for receipt in self.receipts), Decimal("0"))


class BusinessTripReport(BaseReport):
    employee: Employee
    trip_city: str
    trip_start_date: Date
    trip_end_date: Date
    purpose: str
    project: str | None = None
    route: str | None = None
    counterparty: str | None = None
    basis: str | None = None
    approver: str | None = None
    comment: str | None = None

    @model_validator(mode="after")
    def validate_trip_dates(self) -> "BusinessTripReport":
        if self.trip_start_date > self.trip_end_date:
            raise ValueError("Дата начала командировки не может быть позже даты окончания")
        for receipt in self.receipts:
            if not receipt.date:
                continue
            delta_before = (self.trip_start_date - receipt.date).days
            delta_after = (receipt.date - self.trip_end_date).days
            if delta_before > 1 or delta_after > 1:
                raise ValueError("Дата чека должна попадать в период командировки или рядом с ним")
        return self


class RepresentativeExpenseReport(BaseReport):
    initiator: Employee
    event_date: Date
    place: str
    restaurant_name: str
    counterparty: str
    meeting_purpose: str
    participants_company: list[str] = Field(default_factory=list)
    participants_counterparty: list[str] = Field(default_factory=list)
    meeting_result: str


class GiftExpenseReport(BaseReport):
    initiator: Employee
    purchase_date: Date
    gift_name: str
    gift_quantity: int = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    recipients: list[str] = Field(default_factory=list)
    counterparty: str
    occasion: str
    purpose: str

    @field_validator("unit_price", mode="before")
    @classmethod
    def normalize_unit_price(cls, value: object) -> Decimal:
        if isinstance(value, Decimal):
            return value
        if isinstance(value, str):
            value = value.replace(" ", "").replace(",", ".").replace("₽", "")
        return Decimal(str(value))

    @property
    def calculated_gift_amount(self) -> Decimal:
        return self.unit_price * self.gift_quantity
