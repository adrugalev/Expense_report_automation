from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.receipt_parser import _try_read_qr_from_image, parse_qr_payload, parse_receipt_path


FIXTURE_DIR = Path("D:/YandexDisk/Разное/Работа/Huaxun/25-09-30 Командировка в Екатеринбург (Technobuild)")
LEGACY_JPG_DIR = Path("D:/YandexDisk/Разное/Работа/Huaxun/23-10-04 Командировка в Екатеринбург (TechnoBuild)")
LEGACY_JPG_QR_CASES = (
    ("Чек 1110 06.10.23.jpg", "1110.00", "206634"),
    ("Чек 76 04.10.23.jpg", "76.00", "236944"),
    ("Чек 220 04.10.23.jpg", "220.00", "240164"),
)


@pytest.mark.parametrize(("file_name", "amount", "fiscal_document"), LEGACY_JPG_QR_CASES)
def test_decode_yandex_taxi_qr_from_unicode_windows_path(file_name: str, amount: str, fiscal_document: str):
    path = LEGACY_JPG_DIR / file_name
    if not path.exists():
        pytest.skip("local Yandex Taxi JPG receipt fixture is unavailable")

    payload = _try_read_qr_from_image(path)

    assert payload is not None
    assert f"s={amount}" in payload
    assert f"i={fiscal_document}" in payload


@pytest.mark.skipif(not (FIXTURE_DIR / "596_292.pdf").exists(), reason="local Yandex Taxi receipt fixture is unavailable")
def test_parse_yandex_taxi_receipt_596_292():
    receipt = parse_receipt_path(FIXTURE_DIR / "596_292.pdf")

    assert receipt.seller == 'ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "ЯНДЕКС.ТАКСИ"'
    assert receipt.inn == "7704340310"
    assert receipt.check_number == "596"
    assert receipt.fiscal_number == "596"
    assert receipt.shift_number == "65"
    assert receipt.date == date(2025, 10, 2)
    assert receipt.amount == Decimal("292.00")
    assert receipt.expense_type == "такси"
    assert receipt.kkt_number == "0001833970060120"
    assert receipt.fiscal_document_number == "64382"
    assert receipt.fiscal_drive_number == "7380440902200401"
    assert receipt.fiscal_sign == "1353351506"
    assert receipt.qr_raw == "t=20251002T1153&s=292.00&fn=7380440902200401&i=64382&fp=1353351506&n=1"


@pytest.mark.skipif(not (FIXTURE_DIR / "422_381.pdf").exists(), reason="local Yandex Taxi receipt fixture is unavailable")
def test_parse_yandex_taxi_receipt_422_381():
    receipt = parse_receipt_path(FIXTURE_DIR / "422_381.pdf")

    assert receipt.check_number == "422"
    assert receipt.shift_number == "223"
    assert receipt.date == date(2025, 10, 2)
    assert receipt.amount == Decimal("381.00")
    assert receipt.kkt_number == "0004078389002333"
    assert receipt.fiscal_document_number == "204039"
    assert receipt.fiscal_drive_number == "7380440902194882"
    assert receipt.fiscal_sign == "1057078436"
    assert receipt.qr_raw == "t=20251002T0837&s=381.00&fn=7380440902194882&i=204039&fp=1057078436&n=1"


def test_parse_qr_payload():
    parsed = parse_qr_payload("t=20251002T1153&s=292.00&fn=7380440902200401&i=64382&fp=1353351506&n=1")

    assert parsed.receipt_date == date(2025, 10, 2)
    assert parsed.amount == Decimal("292.00")
    assert parsed.fiscal_drive_number == "7380440902200401"
    assert parsed.fiscal_document_number == "64382"
    assert parsed.fiscal_sign == "1353351506"


def test_parse_receipt_prefers_complete_qr_and_skips_requisites_ocr(monkeypatch, tmp_path):
    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr(
        "src.receipt_parser._try_read_qr_from_pdf",
        lambda path: "t=20260504T1258&s=1728.00&fn=7384440900633551&i=26132&fp=4048787786&n=1",
    )
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: "г. Москва, ул. Тестовая, д. 1\nИТОГ 1.00\nФД 11111\nФН 1111111111111111\nФП 111111",
    )

    def fail_requisites_ocr(path):
        raise AssertionError("OCR fallback must not run when QR has fiscal data")

    monkeypatch.setattr("src.receipt_parser._try_ocr_pdf_requisites", fail_requisites_ocr)

    receipt = parse_receipt_path(pdf_path)

    assert receipt.amount == Decimal("1728.00")
    assert receipt.date == date(2026, 5, 4)
    assert receipt.fiscal_document_number == "26132"
    assert receipt.fiscal_drive_number == "7384440900633551"
    assert receipt.fiscal_sign == "4048787786"


def test_parse_pdf_skips_supplemental_ocr_when_amount_fd_and_date_are_present(monkeypatch, tmp_path):
    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("src.receipt_parser._try_read_qr_from_pdf", lambda path: None)
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: "ООО Кафе\nг. Москва, ул. Тестовая, д. 1\nИНН: 7704340310\nИТОГО 1200.00\nФД 4601\n08.10.26 15:26",
    )

    def fail_requisites_ocr(path):
        raise AssertionError("OCR fallback must not run only because FN or FP is absent")

    monkeypatch.setattr("src.receipt_parser._try_ocr_pdf_requisites", fail_requisites_ocr)

    progress = []
    receipt = parse_receipt_path(pdf_path, progress_callback=lambda percent, stage: progress.append((percent, stage)))

    assert receipt.amount == Decimal("1200.00")
    assert receipt.fiscal_document_number == "4601"
    assert progress[0] == (12, "Поиск QR-кода")
    assert progress[-1] == (96, "Подготовка результата")
    assert [percent for percent, _ in progress] == sorted(percent for percent, _ in progress)


@pytest.mark.parametrize("initial_fd", ["ФД 180(T)\nΦ1 0419132341", "ФД 18007"])
def test_parse_pdf_recovers_missing_date_and_damaged_fd_from_requisites_ocr(monkeypatch, tmp_path, initial_fd):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr("src.receipt_parser._try_read_qr_from_pdf", lambda path: None)
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: f"Место расчетов Ресторан Бруннен\nИТОГ 17140.00\nФН 7384440901424529\n{initial_fd}\n00.10.26 15:26",
    )
    calls = []

    def reread(path):
        calls.append(path)
        return "ИНН 7729665662\nФД 18007\nФП 0419132341\n08.10.26 15:26"

    monkeypatch.setattr("src.receipt_parser._try_ocr_pdf_requisites", reread)
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    receipt = parse_receipt_path(pdf_path)

    assert calls == [pdf_path]
    assert receipt.fiscal_document_number == "18007"
    assert receipt.date == date(2026, 10, 8)
    assert receipt.amount == Decimal("17140.00")
    assert receipt.seller == "Brunnen"


def test_missing_qr_date_is_reread_without_overwriting_qr_fd(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "src.receipt_parser._try_read_qr_from_pdf",
        lambda path: "t=invalid&s=1728.00&fn=7384440900633551&i=26132&fp=4048787786&n=1",
    )
    monkeypatch.setattr("src.receipt_parser._try_extract_pdf_text", lambda path: "ИТОГ 1.00\n00.10.26 15:26")
    monkeypatch.setattr(
        "src.receipt_parser._try_ocr_pdf_requisites",
        lambda path: "ФД 18007\n08.10.26 15:26",
    )
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    receipt = parse_receipt_path(pdf_path)

    assert receipt.date == date(2026, 10, 8)
    assert receipt.fiscal_document_number == "26132"
    assert receipt.amount == Decimal("1728.00")


def test_marketing_qr_is_not_selected_as_a_fiscal_receipt():
    from src.receipt_parser import _best_qr_payload, _best_receipt_qr_payload

    marketing = "https://netmonet.co/tip/123456?s=11910&tn=31"
    fiscal = "t=20261016T2047&s=10123.50&fn=7384440901609198&i=9269&fp=3056236885&n=1"
    assert _best_qr_payload([marketing]) is None
    assert _best_receipt_qr_payload([marketing]) is None
    assert _best_receipt_qr_payload([marketing, fiscal]) == fiscal


def test_marketing_qr_does_not_override_cash_register_amount(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "src.receipt_parser._try_read_qr_from_pdf",
        lambda path: "https://netmonet.co/tip/123456?s=11910&tn=31",
    )
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: """
        сумма без нас
        =10123.50
        БЕЗНАЛИЧНЫНИ
        =10123.50
        ООО "ПЯТНИЦА"
        125047. г. Москва. муниципальный округ Тверской. Ул. 1-я Тверская-Ямская. д. 16/23. стр. 1
        место расчетов
        ресторан Гамбринус
        WH 9705211977
        7384440901609198
        ФД 9269
        3056236885
        ПРИХОД
        16.10.26 20:47
        """,
    )
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    def unnecessary_reread(path):
        raise AssertionError("Complete OCR fields should not require another OCR pass")

    monkeypatch.setattr("src.receipt_parser._try_ocr_pdf_requisites", unnecessary_reread)

    receipt = parse_receipt_path(pdf_path)

    assert receipt.amount == Decimal("10123.50")
    assert receipt.fiscal_document_number == "9269"
    assert receipt.date == date(2026, 10, 16)
    assert "Тверская-Ямская" in receipt.address
    assert "16/23" in receipt.address
    assert receipt.address.endswith("стр. 1")


def test_shortened_fd_label_requires_an_independent_reread(monkeypatch, tmp_path):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr("src.receipt_parser._try_read_qr_from_pdf", lambda path: None)
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: "г. Казань, ул. Тестовая, д. 7\nИТОГ 18690.00\nФН 7384440800179627\nд1566\n28.11.25 22:02",
    )
    calls = []

    def reread(path):
        calls.append(path)
        return "ФН 7384440800179627\nФД 15669\n28.11.25 22:02"

    monkeypatch.setattr("src.receipt_parser._try_ocr_pdf_requisites", reread)
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    receipt = parse_receipt_path(pdf_path)

    assert calls == [pdf_path]
    assert receipt.fiscal_document_number == "15669"


@pytest.mark.parametrize("original_address", [
    "г. Казань, ул. Первая-Городская",
    "г. Казань, ул. Перва\nя-Городская, д. 7, стр. 2",
])
def test_complete_qr_still_rereads_an_incomplete_or_wrapped_address(monkeypatch, tmp_path, original_address):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr(
        "src.receipt_parser._try_read_qr_from_pdf",
        lambda path: "t=20261016T2047&s=10123.50&fn=7384440901609198&i=9269&fp=3056236885&n=1",
    )
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: f'ООО "Пример"\n{original_address}',
    )
    monkeypatch.setattr(
        "src.receipt_parser._try_ocr_pdf_requisites",
        lambda path: "г. Казань, ул. Первая-Городская, д. 7, стр. 2\nИТОГ 500.00\nФД 7777",
    )
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    receipt = parse_receipt_path(pdf_path)

    assert receipt.amount == Decimal("10123.50")
    assert receipt.fiscal_document_number == "9269"
    assert receipt.address == "г. Казань, ул. Первая-Городская, д. 7, стр. 2"


@pytest.mark.parametrize(("initial_fd", "reread_fd", "expected_fd"), [
    ("15669", "1566", "15669"),
    ("1566", "15669", "15669"),
    ("12345", "98765", "12345"),
])
def test_conflicting_unlabelled_fd_reads_do_not_silently_replace_a_number(
    monkeypatch, tmp_path, initial_fd, reread_fd, expected_fd,
):
    pdf_path = tmp_path / "scan.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")
    monkeypatch.setattr("src.receipt_parser._try_read_qr_from_pdf", lambda path: None)
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: f"г. Казань, ул. Тестовая, д. 7\nИТОГ 18690.00\nФН 7384440800179627\n{initial_fd}\n28.11.25 22:02",
    )
    monkeypatch.setattr(
        "src.receipt_parser._try_ocr_pdf_requisites",
        lambda path: f"ФН 7384440800179627\n{reread_fd}\n28.11.25 22:02",
    )
    monkeypatch.setattr("src.receipt_parser.lookup_address_online", lambda *args: None)

    receipt = parse_receipt_path(pdf_path)

    assert receipt.fiscal_document_number == expected_fd
    assert "ФД прочитан неоднозначно" in receipt.comment
