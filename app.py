from __future__ import annotations

import hashlib
import html
import sys
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile
from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st

from src.employee_directory import EmployeeDirectory
from pydantic import ValidationError

from src.models import BusinessTripReport, GiftExpenseReport, Receipt, RepresentativeExpenseReport
from src.receipt_parser import ensure_builtin_ocr_runtime, ocr_runtime_status, parse_receipt_file, receipt_from_table_row
from src.representative_autofill import (
    REPRESENTATIVE_AUTOFILL_PROFILES,
    complete_representative_fields,
    profile_by_counterparty,
    results_from_purposes,
)
from src.report_orchestration import representative_receipt_defaults, representative_single_receipt_report
from src.report_builders import BuildResult, BusinessTripBuilder, GiftExpenseBuilder, RepresentativeExpenseBuilder
from src.template_manager import TemplateManager
from src.version import APP_VERSION_DATE, APP_VERSION_REVISION, app_version_history, app_version_label


PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
TEMPLATES_DIR = PROJECT_ROOT / "templates"
OUTPUT_DIR = PROJECT_ROOT / "output"

REPORT_TYPES = {
    "Командировка": "business_trip",
    "Представительские расходы": "representative_expenses",
    "Подарки": "gifts",
}
BUILD_MODE_SEPARATE_PER_RECEIPT = "Отдельный комплект на каждый чек"
BUILD_MODE_SEPARATE_PER_RECEIPT_DIFFERENT_COMPANIES = "Отдельный комплект на каждый чек (разные компании)"
REPORT_TYPE_DEPENDENT_STATE_KEYS = (
    "_generated_documents",
    "_representative_receipt_defaults_signature",
    "_representative_event_date_signature",
    "representative_event_date",
    "representative_place",
    "representative_restaurant_name",
    "participants_counterparty_editor",
)



@st.dialog("История версий")
def _show_version_history_dialog() -> None:
    for entry in app_version_history():
        st.markdown(f"**Версия {entry.revision} от {entry.date}**")
        for change in entry.changes:
            st.markdown(f"- {change}")


def _render_version_history_button() -> None:
    if st.button(app_version_label(), key="version_history_button"):
        _show_version_history_dialog()


def main() -> None:
    st.set_page_config(page_title="Автоматизация отчётных документов", layout="wide")
    _inject_global_css()
    st.title("Автоматизация отчётных документов")
    _render_version_history_button()

    directory = EmployeeDirectory(DATA_DIR)
    template_manager = TemplateManager(TEMPLATES_DIR)
    template_manager.ensure_default_templates()

    with st.sidebar:
        st.header("Файлы")
        report_label = st.selectbox("Тип отчёта", options=list(REPORT_TYPES), index=0, key="report_label")
        report_type = REPORT_TYPES[report_label]
        _sync_report_type_state(report_type)
        receipt_files = st.file_uploader(
            "Чеки",
            type=["pdf", "png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="PDF, JPG, PNG, сканы и фотографии чеков. Распознавание можно поправить вручную.",
            key=f"receipt_files_{st.session_state.get('_receipt_upload_reset', 0)}",
        )
    _ensure_ocr_runtime_for_uploads(receipt_files)

    st.subheader("Инициатор отчёта")
    selected_employee = _employee_selector(directory)
    if selected_employee is None:
        st.warning("Добавьте хотя бы одного сотрудника, чтобы сформировать документы.")
        return

    receipts = _receipt_editor(receipt_files, report_type)
    excel_values: list[str] = []

    with st.form("report_form", border=False):
        with st.container(border=True):
            _inject_report_form_css()
            st.subheader("Данные отчёта")
            if report_type == "business_trip":
                report_date = st.date_input("Дата составления документов", value=date.today(), width=320)
                common_kwargs = {"receipts": receipts, "report_date": report_date}
                report_data = _business_trip_form(selected_employee, common_kwargs)
                build_mode = "single"
            elif report_type == "representative_expenses":
                common_kwargs = {"receipts": receipts}
                report_data = _representative_form(selected_employee, common_kwargs, excel_values, directory)
                build_mode = st.radio(
                    "Если чеков несколько",
                    options=[
                        "Один общий комплект",
                        BUILD_MODE_SEPARATE_PER_RECEIPT,
                        BUILD_MODE_SEPARATE_PER_RECEIPT_DIFFERENT_COMPANIES,
                    ],
                    horizontal=True,
                    disabled=len(receipts) < 2,
                )
            else:
                common_kwargs = {"receipts": receipts}
                report_data = _gift_form(selected_employee, common_kwargs, excel_values)
                build_mode = "single"

        st.markdown(
            f"""
            <div class="generation-summary">
                <p>Будет сформировано документов: {len(template_manager.templates_for(report_type))}</p>
                <p>Чеков: {len(receipts)}</p>
                <p>Итоговая сумма: {sum((receipt.amount for receipt in receipts), Decimal("0"))}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        submitted = st.form_submit_button("Сформировать документы", type="primary")

    if submitted:
        st.session_state.pop("_generated_documents", None)
        try:
            if report_type == "business_trip":
                report = BusinessTripReport(**report_data)
                builder = BusinessTripBuilder(template_manager, OUTPUT_DIR)
            elif report_type == "representative_expenses":
                report = RepresentativeExpenseReport(**report_data)
                builder = RepresentativeExpenseBuilder(template_manager, OUTPUT_DIR)
            else:
                report = GiftExpenseReport(**report_data)
                builder = GiftExpenseBuilder(template_manager, OUTPUT_DIR)
            if report_type == "representative_expenses" and build_mode == BUILD_MODE_SEPARATE_PER_RECEIPT:
                result = _build_representative_per_receipt(builder, report)
            elif report_type == "representative_expenses" and build_mode == BUILD_MODE_SEPARATE_PER_RECEIPT_DIFFERENT_COMPANIES:
                result = _build_representative_per_receipt_different_companies(builder, report)
            else:
                result = builder.build(report)
        except Exception as exc:
            st.error(_humanize_form_error(exc))
            return
        if result.warnings:
            st.warning("Есть предупреждения по плейсхолдерам:\n" + "\n".join(result.warnings))
        _store_generated_result(result)
    _render_generated_result()


def _sync_report_type_state(report_type: str) -> None:
    previous_type = st.session_state.get("_active_report_type")
    if previous_type == report_type:
        return
    if previous_type is not None:
        _clear_report_type_dependent_state()
    st.session_state["_active_report_type"] = report_type


def _clear_report_type_dependent_state() -> None:
    for key in REPORT_TYPE_DEPENDENT_STATE_KEYS:
        st.session_state.pop(key, None)
    for key in list(st.session_state):
        if (
            key.startswith("receipt_editor_")
            or key.startswith("receipt_files_")
            or key.startswith("download_generated_document_")
            or key.startswith("participants_company_")
        ):
            st.session_state.pop(key, None)
    st.session_state["_receipt_upload_reset"] = int(st.session_state.get("_receipt_upload_reset", 0)) + 1


def _inject_global_css() -> None:
    st.markdown(
        """
        <style>
        h1 {
            padding-bottom: 0 !important;
        }

        div.st-key-version_history_button {
            margin: 0;
            padding: 0;
        }

        div.st-key-version_history_button button,
        div.st-key-version_history_button button:hover,
        div.st-key-version_history_button button:focus,
        div.st-key-version_history_button button:active {
            align-items: flex-start;
            background: transparent;
            border: 0;
            box-shadow: none;
            color: rgba(49, 51, 63, 0.6);
            cursor: pointer;
            font-family: inherit;
            font-size: 0.875rem;
            font-weight: 400;
            line-height: 1.6;
            min-height: 0;
            padding: 0;
        }

        div.st-key-version_history_button button p {
            color: inherit;
            font-family: inherit;
            font-size: inherit;
            font-weight: inherit;
            line-height: inherit;
            margin: 0;
        }

        div[data-testid="stFormSubmitButton"] button,
        div[data-testid="stFormSubmitButton"] button[kind="primary"],
        button[data-testid="stBaseButton-primary"] {
            background-color: #16a34a;
            border-color: #16a34a;
            color: #ffffff;
        }
        div[data-testid="stFormSubmitButton"] button:hover,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover {
            background-color: #15803d;
            border-color: #15803d;
            color: #ffffff;
        }
        div[data-testid="stFormSubmitButton"] button:focus,
        div[data-testid="stFormSubmitButton"] button[kind="primary"]:focus,
        button[data-testid="stBaseButton-primary"]:focus {
            box-shadow: 0 0 0 0.12rem rgba(22, 163, 74, 0.35);
            color: #ffffff;
        }
        .employee-summary-card {
            display: flex;
            align-items: center;
            width: 480px;
            max-width: 100%;
            min-height: 6.5rem;
            padding: 0.75rem 1rem;
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 0.5rem;
            margin-top: 0.75rem;
            box-sizing: border-box;
        }
        .employee-summary {
            padding: 0.15rem 0;
        }
        .employee-summary p {
            margin: 0 0 0.42rem;
            line-height: 1.25;
        }
        .employee-summary p:last-child {
            margin-bottom: 0;
        }
        .generation-summary {
            margin: 1rem 0 0.65rem;
        }
        .generation-summary p {
            margin: 0 0 0.45rem;
            line-height: 1.25;
        }
        .generation-summary p:last-child {
            margin-bottom: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _employee_selector(directory: EmployeeDirectory):
    options = directory.options()
    selected = None
    if options:
        label = st.selectbox("Инициатор отчёта", options=options, index=0, label_visibility="collapsed", width=480)
        selected = directory.get_by_label(label)
    if selected:
        st.markdown(
            f"""
                <div class="employee-summary-card">
                <div class="employee-summary">
                    <p><strong>ФИО:</strong> {html.escape(selected.full_name)}</p>
                    <p><strong>Должность:</strong> {html.escape(selected.position)}</p>
                    <p><strong>Компания:</strong> {html.escape(selected.company or "-")}</p>
                    <p><strong>Телефон:</strong> {html.escape(selected.phone or "-")}</p>
                    <p><strong>Email:</strong> {html.escape(selected.email or "-")}</p>
                </div>
                </div>
            """,
            unsafe_allow_html=True,
        )

    return selected


def _receipt_editor(receipt_files, report_type: str) -> list[Receipt]:
    st.subheader("Чеки")
    parsed: list[Receipt] = []
    for uploaded in receipt_files or []:
        receipt = _parse_uploaded_receipt_cached(uploaded).model_copy()
        if report_type == "gifts":
            receipt.expense_type = "подарки"
        elif report_type == "representative_expenses":
            receipt.expense_type = "ресторан"
        parsed.append(receipt)
    if not parsed:
        parsed = [Receipt(file_name="manual", amount=Decimal("1.00"), expense_type="прочее")]
    parse_warnings = [
        f"{receipt.file_name}: {receipt.comment}"
        for receipt in parsed
        if receipt.comment and ("Сумма не распознана" in receipt.comment or "Проверьте распознанные данные" in receipt.comment)
    ]
    if parse_warnings:
        st.warning("Проверьте распознавание чеков:\n\n" + "\n".join(parse_warnings))
        if any("OCR" in warning for warning in parse_warnings):
            status = ocr_runtime_status()
            with st.expander("Диагностика OCR"):
                st.write(f"Python: `{sys.version.split()[0]}`")
                st.write(f"Путь: `{sys.executable}`")
                st.write(f"OCR: {status.message}")
                install_error = st.session_state.get("_receipt_ocr_install_error")
                if install_error:
                    st.write(f"Последняя ошибка установки: {install_error}")
            if st.button("Установить OCR для сканов", type="secondary", key="install_receipt_ocr_after_warning"):
                with st.spinner("Устанавливаю встроенное распознавание чеков..."):
                    status = ensure_builtin_ocr_runtime()
                if status.available:
                    st.session_state.pop("_receipt_parse_cache", None)
                    st.success(f"OCR для сканов готов: {status.engine}")
                    st.rerun()
                st.session_state["_receipt_ocr_install_error"] = status.message
                st.error(status.message)
    frame = pd.DataFrame(
        [
            {
                "file_name": receipt.file_name,
                "date": receipt.date.isoformat() if receipt.date else "",
                "seller": receipt.seller or "",
                "address": receipt.address or "",
                "inn": receipt.inn or "",
                "amount": str(receipt.amount),
                "expense_type": receipt.expense_type,
                "route": receipt.route or "",
                "check_number": _receipt_attr(receipt, "check_number") or _receipt_attr(receipt, "fiscal_number"),
                "fiscal_document_number": _receipt_attr(receipt, "fiscal_document_number"),
                "fiscal_drive_number": _receipt_attr(receipt, "fiscal_drive_number"),
                "fiscal_sign": _receipt_attr(receipt, "fiscal_sign"),
                "comment": receipt.comment or "",
            }
            for receipt in parsed
        ]
    )
    edited = st.data_editor(
        frame,
        num_rows="dynamic",
        use_container_width=True,
        key=_receipt_editor_key(report_type, parsed),
    )
    receipts: list[Receipt] = []
    for row in edited.to_dict("records"):
        receipt = receipt_from_table_row(row)
        if report_type == "gifts":
            receipt.expense_type = "подарки"
        elif report_type == "representative_expenses":
            receipt.expense_type = "ресторан"
        receipts.append(receipt)
    return receipts


def _receipt_editor_key(report_type: str, receipts: list[Receipt]) -> str:
    signature = "|".join(
        (
            f"{receipt.file_name}:{receipt.date or ''}:{receipt.seller or ''}:{receipt.address or ''}:"
            f"{receipt.amount}:{receipt.expense_type}:{receipt.fiscal_document_number or ''}:"
            f"{receipt.fiscal_drive_number or ''}:{receipt.fiscal_sign or ''}"
        )
        for receipt in receipts
    )
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:12]
    reset = st.session_state.get("_receipt_upload_reset", 0)
    return f"receipt_editor_{report_type}_{reset}_{APP_VERSION_REVISION}_{digest}"


def _ensure_ocr_runtime_for_uploads(receipt_files) -> None:
    if not receipt_files:
        return
    if not any(Path(uploaded.name).suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg"} for uploaded in receipt_files):
        return

    status = ocr_runtime_status()
    if status.available:
        return

    if not st.session_state.get("_receipt_ocr_install_attempted"):
        with st.spinner("Подготавливаю встроенное распознавание чеков..."):
            status = ensure_builtin_ocr_runtime()
        st.session_state["_receipt_ocr_install_attempted"] = True
        if status.available:
            st.session_state.pop("_receipt_parse_cache", None)
            st.success(f"OCR для сканов готов: {status.engine}")
            st.rerun()
        st.session_state["_receipt_ocr_install_error"] = status.message


def _parse_uploaded_receipt_cached(uploaded) -> Receipt:
    payload = uploaded.getvalue()
    cache_key = f"v{APP_VERSION_DATE}:{APP_VERSION_REVISION}:{uploaded.name}:{len(payload)}:{hashlib.sha1(payload).hexdigest()}"
    cache = st.session_state.setdefault("_receipt_parse_cache", {})
    if cache_key not in cache:
        cache[cache_key] = parse_receipt_file(BytesIO(payload), uploaded.name)
    return cache[cache_key]


def _store_generated_result(result: BuildResult) -> None:
    st.session_state["_generated_documents"] = {
        "warnings": list(result.warnings),
        "files": [
            {
                "name": file_path.name,
                "data": file_path.read_bytes(),
            }
            for file_path in result.files
        ],
    }


def _render_generated_result() -> None:
    generated = st.session_state.get("_generated_documents")
    if not generated:
        return
    st.success("Документы сформированы.")
    files = generated["files"]
    for index, item in enumerate(files):
        st.download_button(
            item["name"],
            data=item["data"],
            file_name=item["name"],
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key=f"download_generated_document_{index}_{item['name']}",
            on_click="ignore",
        )
    if len(files) > 1:
        st.download_button(
            "Скачать ZIP со всеми документами",
            data=_documents_zip_bytes(files),
            file_name="Документы_отчета.zip",
            mime="application/zip",
            key="download_generated_documents_zip",
            on_click="ignore",
        )


def _documents_zip_bytes(files: list[dict[str, bytes]]) -> bytes:
    buffer = BytesIO()
    used_names: set[str] = set()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as zip_file:
        for item in files:
            name = _unique_archive_name(str(item["name"]), used_names)
            zip_file.writestr(name, item["data"])
    return buffer.getvalue()


def _unique_archive_name(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        used_names.add(name)
        return name
    stem = Path(name).stem
    suffix = Path(name).suffix
    index = 1
    while True:
        candidate = f"{stem}_{index}{suffix}"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        index += 1


def _receipt_attr(receipt: Receipt, name: str) -> str:
    value = getattr(receipt, name, None)
    return "" if value is None else str(value)


def _business_trip_form(employee, common_kwargs):
    default_start_date, default_end_date = _receipt_date_bounds(common_kwargs["receipts"])
    trip_city = st.text_input("Город командировки *", width=480)
    purpose = st.text_area("Цель поездки *", height=80, width=480)
    trip_start_date = st.date_input("Дата начала командировки", value=default_start_date)
    trip_end_date = st.date_input("Дата окончания командировки", value=default_end_date)
    return {
        "employee": employee,
        "trip_city": trip_city,
        "trip_start_date": trip_start_date,
        "trip_end_date": trip_end_date,
        "purpose": purpose,
        "project": "",
        "route": "",
        "counterparty": "",
        "basis": "",
        "approver": None,
        "comment": "",
        **common_kwargs,
    }


def _receipt_date_bounds(receipts: list[Receipt]) -> tuple[date, date]:
    receipt_dates = sorted(receipt.date for receipt in receipts if receipt.date)
    if receipt_dates:
        return receipt_dates[0], receipt_dates[-1]
    today = date.today()
    return today, today


def _humanize_form_error(exc: Exception) -> str:
    messages: list[str] = []
    if isinstance(exc, ValidationError):
        messages = [str(error.get("msg", "")) for error in exc.errors()]
    else:
        messages = [str(exc)]
    joined = " ".join(messages)
    if "Дата чека должна попадать" in joined:
        return (
            "Проверьте даты командировки: даты чеков должны попадать в период командировки "
            "или на один день до/после него. Измените даты командировки или проверьте даты чеков."
        )
    if "Дата чека не может быть позже" in joined:
        return "Проверьте дату составления документов: она не должна быть раньше даты чека."
    if "Field required" in joined or "Поле обязательно" in joined:
        return "Заполните обязательные поля формы."
    return f"Проверьте данные формы: {messages[0]}"


def _representative_form(employee, common_kwargs, excel_values: list[str], directory: EmployeeDirectory):
    restaurant_name_default, place_default = _representative_receipt_defaults(common_kwargs["receipts"])
    _apply_representative_receipt_defaults(common_kwargs["receipts"], restaurant_name_default, place_default)
    _apply_representative_event_date_default(common_kwargs["receipts"])
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown('<div class="report-field-label">Дата составления документов</div>', unsafe_allow_html=True)
        report_date = st.date_input(
            "Дата составления документов",
            value=date.today(),
            width=320,
            label_visibility="collapsed",
        )
        event_date = st.date_input(
            "Дата мероприятия",
            value=_representative_event_date_default(common_kwargs["receipts"]),
            width=320,
            key="representative_event_date",
        )
        place = st.text_input("Место проведения", key="representative_place")
        restaurant_name = st.text_input("Название ресторана / кафе", key="representative_restaurant_name")
        counterparty = st.text_input("Контрагент / организация")
        meeting_purpose = st.text_area("Цель встречи", height=120)
        meeting_result = st.text_area("Результат встречи")
    with right:
        participants_company = _company_participants_selector(
            directory,
            employee,
            columns_per_row=1,
            label_class="report-field-label participants-company-label",
        )
        participants_counterparty = _counterparty_participants_editor()
        _representative_lazy_hint()
    return _autofill_representative_missing_fields(
        {
            "initiator": employee,
            "event_date": event_date,
            "place": place,
            "restaurant_name": restaurant_name,
            "counterparty": counterparty,
            "meeting_purpose": meeting_purpose,
            "participants_company": participants_company,
            "participants_counterparty": participants_counterparty,
            "meeting_result": meeting_result,
            "report_date": report_date,
            **common_kwargs,
        }
    )


def _autofill_representative_missing_fields(data: dict) -> dict:
    profile = _representative_autofill_profile(data)
    return complete_representative_fields(data, profile)


def _representative_results_from_purposes(purpose_text: str) -> list[str]:
    return results_from_purposes(purpose_text)


def _representative_event_date_default(receipts: list[Receipt]) -> date:
    receipt_dates = sorted(receipt.date for receipt in receipts if receipt.date)
    return receipt_dates[0] if receipt_dates else date.today()


def _apply_representative_event_date_default(receipts: list[Receipt]) -> None:
    signature = "|".join(f"{receipt.file_name}:{receipt.date or ''}" for receipt in receipts)
    if signature == st.session_state.get("_representative_event_date_signature"):
        return
    st.session_state["_representative_event_date_signature"] = signature
    if any(receipt.date for receipt in receipts):
        st.session_state["representative_event_date"] = _representative_event_date_default(receipts)


def _apply_gift_purchase_date_default(receipts: list[Receipt]) -> None:
    signature = "|".join(f"{receipt.file_name}:{receipt.date or ''}" for receipt in receipts)
    if signature == st.session_state.get("_gift_purchase_date_signature"):
        return
    st.session_state["_gift_purchase_date_signature"] = signature
    if any(receipt.date for receipt in receipts):
        st.session_state["gift_purchase_date"] = _representative_event_date_default(receipts)


def _representative_autofill_profile(data: dict) -> dict:
    signature = _representative_autofill_signature(data)
    assignments = st.session_state.setdefault("_representative_autofill_assignments", {})
    if signature in assignments:
        counterparty = assignments[signature]
        return _representative_profile_by_counterparty(counterparty)

    recent = list(st.session_state.get("_representative_recent_counterparties", []))
    seed = sum(ord(char) for char in signature)
    profiles = REPRESENTATIVE_AUTOFILL_PROFILES
    candidates = [
        profile
        for profile in profiles
        if profile["counterparty"] not in set(recent[-3:])
    ] or profiles
    profile = candidates[seed % len(candidates)]

    assignments[signature] = profile["counterparty"]
    recent.append(profile["counterparty"])
    st.session_state["_representative_recent_counterparties"] = recent[-6:]
    return profile


def _representative_autofill_signature(data: dict) -> str:
    receipts = data.get("receipts") or []
    receipt_parts = [
        (
            f"{_receipt_value(receipt, 'file_name')}:{_receipt_value(receipt, 'date') or ''}:"
            f"{_receipt_value(receipt, 'amount')}:{_receipt_value(receipt, 'seller') or ''}:"
            f"{_receipt_value(receipt, 'address') or ''}"
        )
        for receipt in receipts
    ]
    initiator = data.get("initiator")
    initiator_key = getattr(initiator, "id", None) or getattr(initiator, "full_name", "")
    form_parts = [
        str(data.get(key) or "")
        for key in ("event_date", "place", "restaurant_name", "report_date")
    ]
    return "|".join([str(data.get("_autofill_variant") or ""), str(initiator_key), *form_parts, *receipt_parts])


def _receipt_value(receipt, field: str):
    if isinstance(receipt, dict):
        return receipt.get(field)
    return getattr(receipt, field, None)


def _representative_profile_by_counterparty(counterparty: str) -> dict:
    return profile_by_counterparty(counterparty)


def _counterparty_participants_editor() -> list[str]:
    st.markdown('<div class="counterparty-participants-spacer"></div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="report-field-label counterparty-participants-label">Участники со стороны контрагента</div>',
        unsafe_allow_html=True,
    )
    frame = pd.DataFrame([{"ФИО": "", "Должность": ""}])
    edited = st.data_editor(
        frame,
        num_rows="dynamic",
        hide_index=True,
        use_container_width=True,
        height=210,
        key="participants_counterparty_editor",
        column_config={
            "ФИО": st.column_config.TextColumn("ФИО", width="medium"),
            "Должность": st.column_config.TextColumn("Должность", width="medium"),
        },
    )
    return _counterparty_participant_rows_to_lines(edited)


def _representative_lazy_hint() -> None:
    st.markdown(
        """
        <div class="representative-lazy-hint">
            Поля про контрагента, цель, результат и участников контрагента можно оставить пустыми.
            Если вы сегодня желаете лениться или так хорошо посидели, что не можете вспомнить имён
            и название кафе, приложение само придумает реалистичные фиктивные данные.
            Но потом не обессудьте :)
        </div>
        """,
        unsafe_allow_html=True,
    )


def _counterparty_participant_rows_to_lines(rows) -> list[str]:
    if isinstance(rows, pd.DataFrame):
        records = rows.to_dict("records")
    else:
        records = list(rows or [])

    participants: list[str] = []
    for row in records:
        name = str(row.get("ФИО", "") or "").strip()
        position = str(row.get("Должность", "") or "").strip()
        if not name:
            continue
        participants.append(f"{name}, {position}" if position else name)
    return participants


def _representative_receipt_defaults(receipts: list[Receipt]) -> tuple[str, str]:
    return representative_receipt_defaults(receipts)


def _apply_representative_receipt_defaults(receipts: list[Receipt], restaurant_name: str, place: str) -> None:
    signature = "|".join(
        f"{receipt.file_name}:{receipt.seller or ''}:{receipt.address or ''}:{receipt.fiscal_document_number or ''}"
        for receipt in receipts
    )
    if signature == st.session_state.get("_representative_receipt_defaults_signature"):
        return
    st.session_state["_representative_receipt_defaults_signature"] = signature
    if place:
        st.session_state["representative_place"] = place
    if restaurant_name:
        st.session_state["representative_restaurant_name"] = restaurant_name


def _company_participants_selector(
    directory: EmployeeDirectory,
    initiator,
    columns_per_row: int = 3,
    label_class: str = "report-field-label",
) -> list[str]:
    st.markdown(f'<div class="{label_class}">Участники со стороны компании</div>', unsafe_allow_html=True)
    selected: list[str] = []
    employees = directory.sorted_employees()
    if not employees:
        return selected
    st.markdown('<div class="participants-grid-anchor"></div>', unsafe_allow_html=True)
    initiator_key = getattr(initiator, "id", None) or getattr(initiator, "full_name", "initiator")
    for row_start in range(0, len(employees), columns_per_row):
        columns = st.columns(columns_per_row, gap="small")
        for offset, (column, employee) in enumerate(zip(columns, employees[row_start : row_start + columns_per_row])):
            index = row_start + offset
            employee_key = employee.id or employee.full_name or str(index)
            with column:
                checked = st.checkbox(
                    employee.full_name,
                    value=employee.id == initiator.id,
                    key=f"participants_company_{initiator_key}_{employee_key}",
                )
            if checked:
                selected.append(employee.full_name)
    return selected


def _inject_report_form_css() -> None:
    st.markdown(
        """
        <style>
        div[data-testid="stForm"] div[data-testid="stDateInput"] {
            max-width: 20rem;
        }
        div[data-testid="stForm"] div[data-testid="stCheckbox"] {
            margin-top: -0.28rem;
            margin-bottom: -0.48rem;
            max-width: 100%;
        }
        div[data-testid="stForm"] div[data-testid="stCheckbox"] label {
            align-items: center;
            gap: 0.45rem;
            min-height: 1.15rem;
            max-width: 100%;
        }
        div[data-testid="stForm"] div[data-testid="stCheckbox"] label p {
            display: block;
            max-width: 100%;
            font-size: 0.8rem;
            line-height: 1.15;
            white-space: normal;
            overflow-wrap: anywhere;
            word-break: normal;
            margin: 0;
        }
        .report-field-label {
            font-size: 0.875rem;
            line-height: 1.25;
            margin: 0 0 0.35rem;
            color: rgb(49, 51, 63);
        }
        .participants-company-label {
            margin-bottom: -0.35rem;
        }
        .participants-grid-anchor {
            height: 0;
            margin: -0.35rem 0 -0.2rem;
        }
        .counterparty-participants-spacer {
            height: 1rem;
        }
        .counterparty-participants-label {
            margin-bottom: 0.55rem;
        }
        .representative-lazy-hint {
            margin-top: 1.8rem;
            width: 100%;
            color: rgb(128, 132, 149);
            font-size: 0.8rem;
            line-height: 1.35;
            text-align: left;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _gift_form(employee, common_kwargs, excel_values: list[str]):
    receipts = common_kwargs["receipts"]
    _apply_gift_purchase_date_default(receipts)
    default_purchase_date = _representative_event_date_default(receipts)
    default_total = sum((receipt.amount for receipt in receipts), Decimal("0"))
    default_amount = default_total if default_total > 0 else Decimal("1.00")
    default_purpose = (
        "Создание долгосрочных деловых отношений, укрепление связей с ключевыми клиентами "
        "и деловыми партнерами и формирование корпоративного имиджа и деловой репутации"
    )
    left, _right = st.columns(2, gap="large")
    with left:
        report_date = st.date_input("Дата составления документов", value=date.today(), width=320)
        purchase_date = st.date_input("Дата покупки", value=default_purchase_date, width=320, key="gift_purchase_date")
    purpose = st.text_area("Цель расходов", value=default_purpose, height=120, width=640)
    return {
        "initiator": employee,
        "purchase_date": purchase_date,
        "gift_name": "подарочная продукция",
        "gift_quantity": 1,
        "unit_price": default_amount,
        "recipients": [],
        "counterparty": "Подарки",
        "occasion": "",
        "purpose": purpose,
        "report_date": report_date,
        **common_kwargs,
    }


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def _read_first_column(file) -> list[str]:
    frame = pd.read_excel(file)
    if frame.empty:
        return []
    return [str(value) for value in frame.iloc[:, 0].dropna().tolist()]


def _representative_single_receipt_report(
    report: RepresentativeExpenseReport,
    receipt: Receipt,
) -> RepresentativeExpenseReport:
    return representative_single_receipt_report(report, receipt)


def _build_representative_per_receipt(builder: RepresentativeExpenseBuilder, report: RepresentativeExpenseReport) -> BuildResult:
    all_files = []
    all_warnings = []
    for receipt in report.receipts:
        single_report = _representative_single_receipt_report(report, receipt)
        result = builder.build(single_report)
        all_files.extend(result.files)
        all_warnings.extend(result.warnings)
    return BuildResult(files=all_files, warnings=all_warnings)


def _build_representative_per_receipt_different_companies(
    builder: RepresentativeExpenseBuilder,
    report: RepresentativeExpenseReport,
) -> BuildResult:
    all_files = []
    all_warnings = []
    for index, receipt in enumerate(report.receipts):
        single_report = _representative_single_receipt_report(report, receipt)
        data = single_report.model_dump()
        data.update(
            {
                "counterparty": "",
                "meeting_purpose": "",
                "meeting_result": "",
                "participants_counterparty": [],
                "_autofill_variant": f"different-company-{index}",
            }
        )
        single_report = RepresentativeExpenseReport(**_autofill_representative_missing_fields(data))
        result = builder.build(single_report)
        all_files.extend(result.files)
        all_warnings.extend(result.warnings)
    return BuildResult(files=all_files, warnings=all_warnings)


if __name__ == "__main__":
    main()
