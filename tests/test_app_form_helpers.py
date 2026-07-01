from datetime import date
from decimal import Decimal
from io import BytesIO
from zipfile import ZipFile

from pydantic import ValidationError
import streamlit as st

from app import (
    REPRESENTATIVE_AUTOFILL_PROFILES,
    _autofill_representative_missing_fields,
    _build_representative_per_receipt_different_companies,
    _sync_report_type_state,
    _counterparty_participant_rows_to_lines,
    _documents_zip_bytes,
    _humanize_form_error,
    _receipt_date_bounds,
    _representative_event_date_default,
    _representative_single_receipt_report,
)
from src.models import BusinessTripReport, Employee, Receipt, RepresentativeExpenseReport
from src.report_builders import BuildResult


def test_receipt_date_bounds_use_uploaded_receipts():
    receipts = [
        Receipt(file_name="1.pdf", date=date(2025, 10, 2), amount=Decimal("381")),
        Receipt(file_name="2.pdf", date=date(2025, 9, 30), amount=Decimal("292")),
    ]

    assert _receipt_date_bounds(receipts) == (date(2025, 9, 30), date(2025, 10, 2))


def test_documents_zip_bytes_contains_all_generated_documents():
    payload = _documents_zip_bytes(
        [
            {"name": "report.docx", "data": b"first"},
            {"name": "report.docx", "data": b"second"},
        ]
    )

    with ZipFile(BytesIO(payload)) as archive:
        assert archive.namelist() == ["report.docx", "report_1.docx"]
        assert archive.read("report.docx") == b"first"
        assert archive.read("report_1.docx") == b"second"


def test_report_type_change_clears_receipt_and_generated_state():
    st.session_state.clear()
    st.session_state["_active_report_type"] = "business_trip"
    st.session_state["_generated_documents"] = {"files": [{"name": "old.docx", "data": b"old"}]}
    st.session_state["receipt_files_0"] = ["old.pdf"]
    st.session_state["receipt_editor_business_trip_0"] = {"edited_rows": {}}
    st.session_state["representative_place"] = "Старый адрес"
    st.session_state["representative_restaurant_name"] = "Старое кафе"
    st.session_state["participants_counterparty_editor"] = []

    _sync_report_type_state("gifts")

    assert st.session_state["_active_report_type"] == "gifts"
    assert st.session_state["_receipt_upload_reset"] == 1
    assert "_generated_documents" not in st.session_state
    assert "receipt_files_0" not in st.session_state
    assert "receipt_editor_business_trip_0" not in st.session_state
    assert "representative_place" not in st.session_state
    assert "representative_restaurant_name" not in st.session_state
    assert "participants_counterparty_editor" not in st.session_state


def test_representative_event_date_default_uses_first_receipt_date():
    receipts = [
        Receipt(file_name="1.pdf", date=date(2026, 4, 9), amount=Decimal("2880"), expense_type="ресторан"),
        Receipt(file_name="2.pdf", date=date(2026, 4, 10), amount=Decimal("3697"), expense_type="ресторан"),
    ]

    assert _representative_event_date_default(receipts) == date(2026, 4, 9)


def test_representative_single_receipt_report_uses_receipt_cafe_address_and_date():
    initiator = Employee(full_name="Баранова Гиляна Басанговна", position="Менеджер по продажам")
    receipts = [
        Receipt(
            file_name="first.pdf",
            date=date(2026, 4, 9),
            seller="Первое кафе",
            address="г. Москва, первый адрес",
            amount=Decimal("1000"),
            expense_type="ресторан",
        ),
        Receipt(
            file_name="second.pdf",
            date=date(2026, 4, 10),
            seller="Второе кафе",
            address="г. Москва, второй адрес",
            amount=Decimal("2000"),
            expense_type="ресторан",
        ),
    ]
    report = RepresentativeExpenseReport(
        initiator=initiator,
        event_date=date(2026, 4, 9),
        place="Общий адрес",
        restaurant_name="Общее кафе",
        counterparty="Coldy",
        meeting_purpose="Цель",
        participants_company=["Баранова Гиляна Басанговна"],
        participants_counterparty=["Иванов Иван, директор"],
        meeting_result="Результат",
        receipts=receipts,
        report_date=date(2026, 6, 30),
    )

    single_report = _representative_single_receipt_report(report, receipts[1])

    assert single_report.receipts == [receipts[1]]
    assert single_report.restaurant_name == "Второе кафе"
    assert single_report.place == "г. Москва, второй адрес"
    assert single_report.event_date == date(2026, 4, 10)
    assert single_report.total_amount == Decimal("2000")


def test_representative_single_receipt_report_does_not_leak_common_place_from_other_receipt():
    initiator = Employee(full_name="Баранова Гиляна Басанговна", position="Менеджер по продажам")
    receipt = Receipt(
        file_name="second.pdf",
        date=date(2026, 4, 10),
        address="г. Москва, второй адрес",
        amount=Decimal("2000"),
        expense_type="ресторан",
    )
    report = RepresentativeExpenseReport(
        initiator=initiator,
        event_date=date(2026, 4, 9),
        place="Адрес первого чека из общей формы",
        restaurant_name="Кафе первого чека из общей формы",
        counterparty="Coldy",
        meeting_purpose="Цель",
        participants_company=["Баранова Гиляна Басанговна"],
        participants_counterparty=["Иванов Иван, директор"],
        meeting_result="Результат",
        receipts=[receipt],
        report_date=date(2026, 6, 30),
    )

    single_report = _representative_single_receipt_report(report, receipt)

    assert single_report.restaurant_name == ""
    assert single_report.place == "г. Москва, второй адрес"


def test_build_representative_per_receipt_different_companies_uses_distinct_counterparties():
    st.session_state.clear()
    initiator = Employee(full_name="Баранова Гиляна Басанговна", position="Менеджер по продажам")
    receipts = [
        Receipt(
            file_name="first.pdf",
            date=date(2026, 4, 9),
            seller="Первое кафе",
            address="г. Москва, первый адрес",
            amount=Decimal("1000"),
            expense_type="ресторан",
        ),
        Receipt(
            file_name="second.pdf",
            date=date(2026, 4, 10),
            seller="Второе кафе",
            address="г. Москва, второй адрес",
            amount=Decimal("2000"),
            expense_type="ресторан",
        ),
    ]
    report = RepresentativeExpenseReport(
        initiator=initiator,
        event_date=date(2026, 4, 9),
        place="Общий адрес",
        restaurant_name="Общее кафе",
        counterparty="Общая компания",
        meeting_purpose="Общая цель",
        participants_company=["Баранова Гиляна Басанговна"],
        participants_counterparty=["Иванов Иван, директор"],
        meeting_result="Общий результат",
        receipts=receipts,
        report_date=date(2026, 6, 30),
    )

    class Builder:
        def __init__(self):
            self.reports = []

        def build(self, single_report):
            self.reports.append(single_report)
            return BuildResult(files=[], warnings=[])

    builder = Builder()

    _build_representative_per_receipt_different_companies(builder, report)

    assert len(builder.reports) == 2
    assert builder.reports[0].counterparty != builder.reports[1].counterparty
    assert builder.reports[0].restaurant_name == "Первое кафе"
    assert builder.reports[1].restaurant_name == "Второе кафе"
    assert builder.reports[0].place == "г. Москва, первый адрес"
    assert builder.reports[1].place == "г. Москва, второй адрес"
    assert builder.reports[0].total_amount == Decimal("1000")
    assert builder.reports[1].total_amount == Decimal("2000")
    assert builder.reports[0].counterparty != "Общая компания"
    assert builder.reports[0].meeting_purpose != "Общая цель"


def test_humanize_trip_receipt_period_error():
    employee = Employee(full_name="Иванов Иван", position="Менеджер")
    try:
        BusinessTripReport(
            employee=employee,
            trip_city="Москва",
            trip_start_date=date(2026, 6, 29),
            trip_end_date=date(2026, 6, 29),
            purpose="Командировка",
            receipts=[Receipt(file_name="check.pdf", date=date(2025, 10, 2), amount=Decimal("381"))],
            report_date=date(2026, 6, 29),
        )
    except ValidationError as exc:
        message = _humanize_form_error(exc)

    assert "Проверьте даты командировки" in message
    assert "input_value" not in message


def test_counterparty_participant_rows_include_positions():
    rows = [
        {"ФИО": "Иванов Иван", "Должность": "директор по развитию"},
        {"ФИО": "Петров Петр", "Должность": ""},
        {"ФИО": "", "Должность": "руководитель проекта"},
    ]

    assert _counterparty_participant_rows_to_lines(rows) == [
        "Иванов Иван, директор по развитию",
        "Петров Петр",
    ]


def test_representative_autofill_fills_empty_business_context():
    data = {
        "event_date": date(2026, 6, 30),
        "place": "Москва",
        "restaurant_name": "Smoke BBQ",
        "report_date": date(2026, 6, 30),
        "counterparty": "",
        "meeting_purpose": "",
        "meeting_result": "",
        "participants_counterparty": [],
    }

    completed = _autofill_representative_missing_fields(data)

    assert completed["counterparty"] in {profile["counterparty"] for profile in REPRESENTATIVE_AUTOFILL_PROFILES}
    assert len(completed["meeting_purpose"].splitlines()) >= 3
    assert len(completed["meeting_result"].splitlines()) >= 3
    assert len(completed["participants_counterparty"]) >= 2
    assert all("," in participant for participant in completed["participants_counterparty"])


def test_representative_autofill_builds_results_from_user_purposes():
    data = {
        "event_date": date(2026, 6, 30),
        "place": "Москва",
        "restaurant_name": "Smoke BBQ",
        "report_date": date(2026, 6, 30),
        "counterparty": "",
        "meeting_purpose": "Обсудить новый проект\nРешить вопрос с монтажом лифтов\nПровести встречу с боссом",
        "meeting_result": "",
        "participants_counterparty": [],
    }

    completed = _autofill_representative_missing_fields(data)

    assert completed["meeting_result"] == (
        "Обсужден новый проект\n"
        "Решен вопрос с монтажом лифтов\n"
        "Достигнута договоренность о встрече с боссом"
    )


def test_representative_autofill_profile_pool_has_twenty_companies():
    counterparties = [profile["counterparty"] for profile in REPRESENTATIVE_AUTOFILL_PROFILES]

    assert len(counterparties) == 20
    assert len(set(counterparties)) == 20


def test_representative_autofill_rotates_recent_counterparties():
    st.session_state.clear()
    employee = Employee(full_name="Баранова Гиляна Басанговна", position="Менеджер по продажам")
    counterparties = []
    last_data = None
    for index in range(4):
        last_data = {
            "initiator": employee,
            "event_date": date(2026, 6, 30),
            "place": f"Москва, место {index}",
            "restaurant_name": "Smoke BBQ",
            "report_date": date(2026, 6, 30),
            "counterparty": "",
            "meeting_purpose": "",
            "meeting_result": "",
            "participants_counterparty": [],
            "receipts": [
                Receipt(
                    file_name=f"check_{index}.pdf",
                    date=date(2026, 6, 30),
                    seller="Smoke BBQ",
                    address="г. Москва, ул. Трубная, д. 18",
                    amount=Decimal("1000"),
                    expense_type="ресторан",
                )
            ],
        }
        counterparties.append(_autofill_representative_missing_fields(last_data)["counterparty"])

    assert len(set(counterparties)) == 4
    assert _autofill_representative_missing_fields(last_data)["counterparty"] == counterparties[-1]


def test_representative_autofill_keeps_user_values():
    data = {
        "event_date": date(2026, 6, 30),
        "place": "Москва",
        "restaurant_name": "Smoke BBQ",
        "report_date": date(2026, 6, 30),
        "counterparty": "ООО «Ручной контрагент»",
        "meeting_purpose": "Ручная цель",
        "meeting_result": "Ручной результат",
        "participants_counterparty": ["Иванов Иван, директор"],
    }

    assert _autofill_representative_missing_fields(data) == data
