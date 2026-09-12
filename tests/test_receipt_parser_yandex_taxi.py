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
        lambda path: "ИТОГ 1.00\nФД 11111\nФН 1111111111111111\nФП 111111",
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


def test_parse_pdf_skips_supplemental_ocr_when_amount_and_fd_are_present(monkeypatch, tmp_path):
    pdf_path = tmp_path / "receipt.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\n")

    monkeypatch.setattr("src.receipt_parser._try_read_qr_from_pdf", lambda path: None)
    monkeypatch.setattr(
        "src.receipt_parser._try_extract_pdf_text",
        lambda path: "ООО Кафе\nИНН: 7704340310\nИТОГО 1200.00\nФД 4601",
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
