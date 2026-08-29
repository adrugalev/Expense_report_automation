from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from src.models import Receipt


BuildMode = Literal["single", "per_receipt", "per_receipt_different_companies"]
ReportStatus = Literal["processing", "completed", "failed"]


class ReceiptUploadReference(BaseModel):
    upload_id: str = Field(min_length=1, max_length=36)
    receipt_index: int = Field(ge=0)


class ReportRequestBase(BaseModel):
    employee_id: str
    report_date: date
    receipts: list[Receipt] = Field(default_factory=list)
    receipt_uploads: list[ReceiptUploadReference] = Field(default_factory=list)


class BusinessTripGenerateRequest(ReportRequestBase):
    report_type: Literal["business_trip"]
    trip_city: str = Field(min_length=1, max_length=255)
    trip_start_date: date
    trip_end_date: date
    purpose: str = Field(min_length=1, max_length=4000)
    project: str | None = Field(default=None, max_length=1000)
    route: str | None = Field(default=None, max_length=2000)
    counterparty: str | None = Field(default=None, max_length=1000)
    basis: str | None = Field(default=None, max_length=1000)
    approver: str | None = Field(default=None, max_length=500)
    comment: str | None = Field(default=None, max_length=4000)
    build_mode: Literal["single"] = "single"


class RepresentativeGenerateRequest(ReportRequestBase):
    report_type: Literal["representative_expenses"]
    event_date: date
    place: str = Field(default="", max_length=1000)
    restaurant_name: str = Field(default="", max_length=500)
    counterparty: str = Field(default="", max_length=1000)
    meeting_purpose: str = Field(default="", max_length=6000)
    participants_company: list[str] = Field(default_factory=list, max_length=100)
    participants_counterparty: list[str] = Field(default_factory=list, max_length=100)
    meeting_result: str = Field(default="", max_length=6000)
    build_mode: BuildMode = "single"


class GiftGenerateRequest(ReportRequestBase):
    report_type: Literal["gifts"]
    purchase_date: date
    gift_name: str = Field(default="подарочная продукция", min_length=1, max_length=1000)
    gift_quantity: int = Field(default=1, gt=0, le=100000)
    unit_price: Decimal = Field(gt=0)
    recipients: list[str] = Field(default_factory=list, max_length=1000)
    counterparty: str = Field(default="Подарки", max_length=1000)
    occasion: str = Field(default="", max_length=2000)
    purpose: str = Field(min_length=1, max_length=6000)
    build_mode: Literal["single"] = "single"


ReportGenerateRequest = Annotated[
    Union[BusinessTripGenerateRequest, RepresentativeGenerateRequest, GiftGenerateRequest],
    Field(discriminator="report_type"),
]


class GeneratedFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int
    download_url: str


class ReportReceiptFileResponse(BaseModel):
    id: str
    name: str
    mime_type: str
    size: int
    amount: Decimal
    download_url: str


class ReportSummaryResponse(BaseModel):
    id: str
    report_type: Literal["business_trip", "representative_expenses", "gifts"]
    status: ReportStatus
    employee_id: str | None
    employee_name: str | None
    build_mode: BuildMode
    total_amount: Decimal
    created_at: datetime
    completed_at: datetime | None
    files_count: int


class ReportDetailResponse(ReportSummaryResponse):
    input: ReportGenerateRequest
    files: list[GeneratedFileResponse]
    receipt_files: list[ReportReceiptFileResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    error_message: str | None = None


class ReportListResponse(BaseModel):
    items: list[ReportSummaryResponse]
    total: int


class ReportTypeResponse(BaseModel):
    id: Literal["business_trip", "representative_expenses", "gifts"]
    name: str
    description: str
    accepted_expense_type: Literal["такси", "ресторан", "подарки"]


class RepresentativeSuggestionRequest(BaseModel):
    signature: str = ""
    recent_counterparties: list[str] = Field(default_factory=list, max_length=10)
    meeting_purpose: str = Field(default="", max_length=6000)


class RepresentativeSuggestionResponse(BaseModel):
    counterparty: str
    meeting_purpose: str
    meeting_result: str
    participants_counterparty: list[str]
