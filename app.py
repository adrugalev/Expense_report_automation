from __future__ import annotations

import hashlib
import html
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
from src.receipt_parser import parse_receipt_file, receipt_from_table_row
from src.report_builders import BuildResult, BusinessTripBuilder, GiftExpenseBuilder, RepresentativeExpenseBuilder
from src.template_manager import TemplateManager
from src.version import app_version_label


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

REPRESENTATIVE_AUTOFILL_PROFILES = [
    {
        "counterparty": "Upside Development",
        "participants": [
            ("Смирнов Алексей", "директор по развитию"),
            ("Кузнецова Мария", "руководитель проектного офиса"),
        ],
        "purposes": [
            "обсуждение перспектив сотрудничества по лифтовому оборудованию для строящихся объектов",
            "презентация технических решений и вариантов комплектации лифтового оборудования",
            "согласование порядка обмена проектной документацией и исходными данными",
            "обсуждение сроков подготовки коммерческого предложения и дальнейших переговоров",
        ],
        "results": [
            "проведена презентация технических решений по лифтовому оборудованию",
            "получена предварительная информация по планируемым объектам и срокам реализации",
            "согласован порядок передачи исходных данных для подготовки коммерческого предложения",
            "достигнута договоренность о дальнейшем рабочем взаимодействии с проектной командой",
        ],
    },
    {
        "counterparty": "ГК «Аквилон»",
        "participants": [
            ("Орлов Дмитрий", "руководитель службы закупок"),
            ("Васильева Елена", "главный инженер проекта"),
        ],
        "purposes": [
            "обсуждение потребности в лифтовом оборудовании для текущих девелоперских проектов",
            "согласование технических требований к оборудованию и сроков поставки",
            "обсуждение условий участия в последующих закупочных процедурах",
            "определение дальнейших шагов по подготовке технико-коммерческого предложения",
        ],
        "results": [
            "обсуждены технические требования по текущим проектам компании",
            "получены ориентиры по срокам поставки и ожидаемой комплектации оборудования",
            "согласована подготовка предварительного технико-коммерческого предложения",
            "зафиксирована договоренность о повторной встрече после анализа проектной документации",
        ],
    },
    {
        "counterparty": "АО «Мосинжпроект»",
        "participants": [
            ("Белов Андрей", "руководитель направления инженерных систем"),
            ("Николаева Ольга", "менеджер проекта"),
        ],
        "purposes": [
            "обсуждение возможности поставки лифтового оборудования для объектов генерального подрядчика",
            "уточнение требований к сертификации, срокам производства и монтажному сопровождению",
            "обсуждение порядка взаимодействия с проектными и закупочными подразделениями",
            "согласование перечня материалов для последующей технической проработки",
        ],
        "results": [
            "уточнены базовые технические требования к оборудованию и комплекту документации",
            "согласован перечень материалов для дальнейшей технической проработки",
            "определены ответственные контактные лица со стороны контрагента",
            "достигнута договоренность о подготовке предложения после получения исходных данных",
        ],
    },
    {
        "counterparty": "Coldy",
        "participants": [
            ("Федоров Илья", "директор по строительству"),
            ("Соколова Наталья", "руководитель отдела комплектации"),
        ],
        "purposes": [
            "обсуждение перспектив поставки лифтового оборудования для жилых и коммерческих объектов",
            "презентация реализованных проектов и продуктовой линейки компании",
            "согласование предварительных технических параметров и требований к отделке кабин",
            "обсуждение сроков подготовки предложения и формата дальнейшей коммуникации",
        ],
        "results": [
            "представлены реализованные проекты и возможные технические решения",
            "получены предварительные требования к параметрам оборудования и отделке кабин",
            "согласован формат дальнейшей коммуникации по техническим вопросам",
            "достигнута договоренность о подготовке предварительного предложения",
        ],
    },
    {
        "counterparty": "ГК «Самолет»",
        "participants": [
            ("Крылов Максим", "руководитель направления закупок"),
            ("Алексеева Ирина", "главный специалист по инженерным системам"),
        ],
        "purposes": [
            "обсуждение потребности в лифтовом оборудовании для жилых кварталов компании",
            "презентация вариантов комплектации и отделки кабин для типовых секций",
            "согласование порядка предоставления проектных данных для технической оценки",
            "обсуждение сроков подготовки коммерческого предложения и дальнейшей коммуникации",
        ],
        "results": [
            "обсуждены параметры лифтового оборудования для перспективных объектов",
            "получены предварительные требования к комплектации и отделке кабин",
            "согласован порядок обмена проектной документацией",
            "достигнута договоренность о подготовке предварительного предложения",
        ],
    },
    {
        "counterparty": "MR Group",
        "participants": [
            ("Захаров Павел", "директор по комплектации"),
            ("Мельникова Анна", "руководитель проекта"),
        ],
        "purposes": [
            "обсуждение технических решений для объектов бизнес-класса",
            "презентация реализованных поставок и возможных вариантов кастомизации кабин",
            "уточнение требований к срокам производства, логистике и монтажному сопровождению",
            "согласование дальнейших шагов по подготовке технико-коммерческого предложения",
        ],
        "results": [
            "представлены технические решения и примеры реализованных проектов",
            "уточнены требования к внешней отделке кабин и срокам поставки",
            "определен перечень исходных данных для коммерческой проработки",
            "согласован формат дальнейшего взаимодействия с проектной командой",
        ],
    },
    {
        "counterparty": "Level Group",
        "participants": [
            ("Новиков Роман", "руководитель отдела закупок"),
            ("Громова Екатерина", "главный инженер проекта"),
        ],
        "purposes": [
            "обсуждение перспектив поставки лифтового оборудования для текущих проектов",
            "согласование технических параметров, требований к безопасности и сертификации",
            "обсуждение вариантов отделки кабин и интеграции с проектными решениями",
            "определение сроков подготовки предложения и последующей рабочей встречи",
        ],
        "results": [
            "согласованы базовые технические параметры для предварительного расчета",
            "получены ориентиры по требованиям к отделке и комплектации оборудования",
            "определены контактные лица для обмена проектной документацией",
            "достигнута договоренность о следующем этапе технической проработки",
        ],
    },
    {
        "counterparty": "ГК «ФСК»",
        "participants": [
            ("Егоров Сергей", "руководитель тендерного направления"),
            ("Павлова Виктория", "менеджер проекта"),
        ],
        "purposes": [
            "обсуждение условий участия в закупочных процедурах по лифтовому оборудованию",
            "уточнение требований к технической документации и коммерческой части предложения",
            "презентация производственных возможностей и реализованных поставок",
            "согласование перечня материалов для последующей квалификационной оценки",
        ],
        "results": [
            "обсуждены требования к участию в будущих закупочных процедурах",
            "уточнен перечень документов для предварительной квалификации поставщика",
            "представлены производственные возможности и опыт реализованных проектов",
            "согласована подготовка материалов для дальнейшего рассмотрения",
        ],
    },
    {
        "counterparty": "ПИК",
        "participants": [
            ("Лебедев Артем", "руководитель направления комплектации"),
            ("Сафонова Юлия", "главный специалист по инженерному оборудованию"),
        ],
        "purposes": [
            "обсуждение поставки лифтового оборудования для объектов массового жилищного строительства",
            "согласование требований к типовым решениям, срокам производства и сервисной поддержке",
            "обсуждение возможной унификации комплектации для нескольких строительных площадок",
            "определение порядка подготовки предварительного коммерческого предложения",
        ],
        "results": [
            "обсуждены требования к типовым решениям для жилых объектов",
            "получены ориентиры по срокам поставки и ожидаемым объемам",
            "согласован перечень данных для технического расчета",
            "достигнута договоренность о подготовке предварительного предложения",
        ],
    },
    {
        "counterparty": "ГК «Кортрос»",
        "participants": [
            ("Семенов Антон", "директор по строительству"),
            ("Калинина Оксана", "руководитель проектной группы"),
        ],
        "purposes": [
            "обсуждение потребности в лифтовом оборудовании для текущих жилых проектов",
            "уточнение технических требований к грузоподъемности, скорости и отделке кабин",
            "презентация реализованных поставок для сопоставимых объектов",
            "согласование дальнейшего порядка обмена проектной документацией",
        ],
        "results": [
            "уточнены базовые технические требования к оборудованию",
            "представлены примеры реализованных поставок и варианты отделки",
            "согласован перечень исходных данных для расчета",
            "определены дальнейшие шаги по подготовке предложения",
        ],
    },
    {
        "counterparty": "ГК «Инград»",
        "participants": [
            ("Комаров Денис", "руководитель отдела закупок"),
            ("Жукова Марина", "менеджер по комплектации"),
        ],
        "purposes": [
            "обсуждение условий поставки лифтового оборудования для новых очередей строительства",
            "согласование требований к документации, сертификации и графику поставки",
            "обсуждение вариантов отделки кабин с учетом концепции объектов",
            "определение сроков подготовки технико-коммерческого предложения",
        ],
        "results": [
            "обсуждены условия поставки и требования к комплекту документации",
            "получены предварительные параметры оборудования для расчета",
            "согласован формат предоставления коммерческого предложения",
            "достигнута договоренность о дальнейшей технической консультации",
        ],
    },
    {
        "counterparty": "ГК «Пионер»",
        "participants": [
            ("Морозов Илья", "директор по закупкам"),
            ("Тихонова Светлана", "главный инженер проекта"),
        ],
        "purposes": [
            "обсуждение технических решений для лифтового оборудования в жилых комплексах",
            "презентация вариантов отделки кабин и систем диспетчеризации",
            "уточнение требований к срокам изготовления и монтажному сопровождению",
            "согласование порядка подготовки предложения после получения проектных данных",
        ],
        "results": [
            "представлены варианты технических решений и отделки кабин",
            "уточнены требования к срокам производства и монтажному сопровождению",
            "определен перечень документов для подготовки предложения",
            "согласована последующая коммуникация с технической службой",
        ],
    },
    {
        "counterparty": "ГК «Гранель»",
        "participants": [
            ("Чернов Кирилл", "руководитель службы комплектации"),
            ("Фомина Дарья", "менеджер проекта"),
        ],
        "purposes": [
            "обсуждение возможности поставки лифтового оборудования для жилых кварталов",
            "согласование технических параметров и требований к эксплуатационной надежности",
            "обсуждение графика поставки оборудования на строительные площадки",
            "уточнение состава коммерческого предложения и дальнейших шагов",
        ],
        "results": [
            "обсуждены параметры оборудования для перспективных объектов",
            "получены данные по предварительным срокам реализации проектов",
            "согласован порядок подготовки технической части предложения",
            "достигнута договоренность о последующем обмене документацией",
        ],
    },
    {
        "counterparty": "ГК «Эталон»",
        "participants": [
            ("Фролов Алексей", "директор по комплектации"),
            ("Романова Елена", "руководитель направления инженерных систем"),
        ],
        "purposes": [
            "обсуждение лифтового оборудования для объектов комфорт- и бизнес-класса",
            "согласование требований к дизайну кабин, энергоэффективности и сервису",
            "презентация производственных возможностей и реализованных проектов",
            "определение формата дальнейшего технического взаимодействия",
        ],
        "results": [
            "обсуждены требования к дизайну и техническим параметрам оборудования",
            "представлены производственные возможности и примеры поставок",
            "получены ориентиры по ожидаемым срокам реализации объектов",
            "согласована подготовка материалов для внутреннего рассмотрения",
        ],
    },
    {
        "counterparty": "ГК «А101»",
        "participants": [
            ("Соловьев Михаил", "руководитель отдела закупок"),
            ("Гордеева Полина", "главный специалист проектного отдела"),
        ],
        "purposes": [
            "обсуждение потребности в лифтовом оборудовании для объектов комплексного развития территорий",
            "уточнение технических требований к оборудованию и условиям сервисного обслуживания",
            "обсуждение вариантов комплектации для разных типов корпусов",
            "согласование сроков подготовки предварительного предложения",
        ],
        "results": [
            "уточнены требования к оборудованию для разных типов объектов",
            "получены ориентиры по комплектации и сервисному сопровождению",
            "согласован перечень исходных данных для расчета",
            "достигнута договоренность о подготовке предварительных материалов",
        ],
    },
    {
        "counterparty": "Capital Group",
        "participants": [
            ("Волков Дмитрий", "директор по развитию проектов"),
            ("Синицына Алина", "руководитель службы комплектации"),
        ],
        "purposes": [
            "обсуждение премиальных технических решений для объектов высокого класса",
            "презентация вариантов индивидуальной отделки кабин и систем управления",
            "уточнение требований к срокам производства, качеству материалов и сервису",
            "согласование порядка подготовки детализированного коммерческого предложения",
        ],
        "results": [
            "представлены варианты премиальной отделки и технических решений",
            "уточнены требования к материалам, срокам и сервисному сопровождению",
            "определен состав исходных данных для детальной проработки",
            "согласован дальнейший порядок взаимодействия с проектной командой",
        ],
    },
    {
        "counterparty": "ГК «Основа»",
        "participants": [
            ("Борисов Николай", "руководитель направления строительства"),
            ("Ершова Валерия", "менеджер по закупкам"),
        ],
        "purposes": [
            "обсуждение возможностей поставки лифтового оборудования для жилых и апарт-комплексов",
            "согласование предварительных технических параметров и требований к отделке",
            "обсуждение сроков поставки и возможного графика производства",
            "определение перечня материалов для подготовки коммерческого предложения",
        ],
        "results": [
            "обсуждены предварительные технические параметры оборудования",
            "получены требования к отделке кабин и срокам поставки",
            "согласован перечень материалов для коммерческой проработки",
            "зафиксирована договоренность о следующем рабочем контакте",
        ],
    },
    {
        "counterparty": "ГК «Крост»",
        "participants": [
            ("Гусев Андрей", "директор производственно-технического департамента"),
            ("Макарова Нина", "руководитель проектного отдела"),
        ],
        "purposes": [
            "обсуждение технических решений для объектов жилого и общественного назначения",
            "уточнение требований к нестандартным шахтам и вариантам комплектации",
            "презентация опыта поставок для проектов со сложными архитектурными решениями",
            "согласование дальнейшей технической проработки после анализа документации",
        ],
        "results": [
            "обсуждены технические ограничения и возможные варианты комплектации",
            "представлен опыт поставок для сложных архитектурных проектов",
            "согласован порядок передачи проектной документации",
            "достигнута договоренность о технической консультации после анализа исходных данных",
        ],
    },
    {
        "counterparty": "ГК «МонАрх»",
        "participants": [
            ("Рябов Константин", "руководитель отдела снабжения"),
            ("Киселева Ольга", "главный инженер проекта"),
        ],
        "purposes": [
            "обсуждение поставки лифтового оборудования для объектов генерального подряда",
            "уточнение требований к срокам производства, логистике и монтажной готовности",
            "обсуждение документации, необходимой для участия в закупочной процедуре",
            "согласование порядка подготовки технической и коммерческой частей предложения",
        ],
        "results": [
            "обсуждены требования к срокам производства и логистике поставки",
            "получен перечень документов для участия в закупочной процедуре",
            "согласован порядок подготовки технической части предложения",
            "достигнута договоренность о дальнейшем взаимодействии по проекту",
        ],
    },
    {
        "counterparty": "ANTTEQ",
        "participants": [
            ("Поляков Виктор", "директор по строительству"),
            ("Белова Ксения", "руководитель тендерного отдела"),
        ],
        "purposes": [
            "обсуждение возможного участия в поставках лифтового оборудования для объектов генподрядчика",
            "уточнение требований к техническим решениям, срокам и условиям гарантийного обслуживания",
            "презентация производственных возможностей и опыта выполнения комплексных поставок",
            "определение порядка подготовки предложения для последующего тендерного рассмотрения",
        ],
        "results": [
            "представлены производственные возможности и опыт комплексных поставок",
            "уточнены требования к гарантийному обслуживанию и срокам поставки",
            "согласован перечень данных для предварительного расчета",
            "достигнута договоренность о подготовке предложения для тендерного рассмотрения",
        ],
    },
]


def main() -> None:
    st.set_page_config(page_title="Автоматизация отчётных документов", layout="wide")
    _inject_global_css()
    st.title("Автоматизация отчётных документов")
    st.caption(app_version_label())

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
        parsed.append(receipt)
    if not parsed:
        parsed = [Receipt(file_name="manual", amount=Decimal("1.00"), expense_type="прочее")]
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
        key=f"receipt_editor_{report_type}_{st.session_state.get('_receipt_upload_reset', 0)}",
    )
    receipts: list[Receipt] = []
    for row in edited.to_dict("records"):
        receipt = receipt_from_table_row(row)
        if report_type == "gifts":
            receipt.expense_type = "подарки"
        receipts.append(receipt)
    return receipts


def _parse_uploaded_receipt_cached(uploaded) -> Receipt:
    payload = uploaded.getvalue()
    cache_key = f"{uploaded.name}:{len(payload)}:{hashlib.sha1(payload).hexdigest()}"
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
    completed = dict(data)
    user_meeting_purpose = str(completed.get("meeting_purpose") or "").strip()
    if not str(completed.get("counterparty") or "").strip():
        completed["counterparty"] = profile["counterparty"]
    if not user_meeting_purpose:
        completed["meeting_purpose"] = "\n".join(profile["purposes"])
    if not str(completed.get("meeting_result") or "").strip():
        completed["meeting_result"] = (
            "\n".join(_representative_results_from_purposes(user_meeting_purpose))
            if user_meeting_purpose
            else "\n".join(profile["results"])
        )
    if not completed.get("participants_counterparty"):
        completed["participants_counterparty"] = [
            f"{name}, {position}" for name, position in profile["participants"]
        ]
    return completed


def _representative_results_from_purposes(purpose_text: str) -> list[str]:
    results: list[str] = []
    for line in _split_lines(purpose_text):
        normalized = line.strip().rstrip(".;")
        lowered = normalized.lower()
        if lowered.startswith("обсудить "):
            results.append(f"Обсужден{normalized[len('обсудить'):]}".strip())
        elif lowered.startswith("решить "):
            results.append(f"Решен{normalized[len('решить'):]}".strip())
        elif lowered.startswith("договориться "):
            results.append(f"Достигнута договоренность{normalized[len('договориться'):]}".strip())
        elif lowered.startswith("провести встречу"):
            details = normalized[len("провести встречу") :].strip()
            results.append(f"Достигнута договоренность о встрече{' ' + details if details else ''}".strip())
        elif lowered.startswith("согласовать "):
            results.append(f"Согласован{normalized[len('согласовать'):]}".strip())
        elif lowered.startswith("уточнить "):
            results.append(f"Уточнен{normalized[len('уточнить'):]}".strip())
        elif lowered.startswith("презентовать "):
            results.append(f"Проведена презентация{normalized[len('презентовать'):]}".strip())
        else:
            results.append(f"Достигнут результат по задаче: {normalized}")
    return results


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
    for profile in REPRESENTATIVE_AUTOFILL_PROFILES:
        if profile["counterparty"] == counterparty:
            return profile
    return REPRESENTATIVE_AUTOFILL_PROFILES[0]


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
    for receipt in receipts:
        if receipt.expense_type == "ресторан" or receipt.seller or receipt.address:
            return receipt.seller or "", receipt.address or ""
    return "", ""


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
    default_purchase_date = _representative_event_date_default(receipts)
    default_total = sum((receipt.amount for receipt in receipts), Decimal("0"))
    default_amount = default_total if default_total > 0 else Decimal("1.00")
    default_purpose = (
        "Создание долгосрочных деловых отношений, укрепление связей с ключевыми клиентами "
        "и деловыми партнерами и формирование корпоративного имиджа и деловой репутации"
    )
    report_date_col, purchase_date_col = st.columns(2, gap="large")
    with report_date_col:
        report_date = st.date_input("Дата составления документов", value=date.today(), width=320)
    with purchase_date_col:
        purchase_date = st.date_input("Дата покупки", value=default_purchase_date, width=320)
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
    return report.model_copy(
        update={
            "receipts": [receipt],
            "restaurant_name": receipt.seller or "",
            "place": receipt.address or "",
            "event_date": receipt.date or report.event_date,
        }
    )


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
