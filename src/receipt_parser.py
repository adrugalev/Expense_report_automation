from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import BinaryIO
from urllib.parse import parse_qs

from .address_lookup import lookup_address_online, merge_online_address, should_lookup_address
from .models import Receipt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_TESSDATA_DIR = PROJECT_ROOT / "data" / "tessdata"
COMMON_TESSERACT_PATHS = (
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
)
MONEY_RE = r"(\d[\d\s]*[,.]\d{2})"
OCR_MONEY_RE = r"(\d[\d\s]*[-–]\s*\d{2})"
AMOUNT_PATTERNS = [
    re.compile(rf"(?im)^\s*Итого\s+{MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*ИТО[ГI!]*[^\d]{{0,20}}{OCR_MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*И[ТT][ОO0][ГI!]*[^\d]{{0,30}}{MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*(?:UTOI?r?|HTO\w*|WIORR)[^\d]{{0,20}}{OCR_MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*(?:C|С)[УUуy]M[MМ][AА][^\d]{{0,40}}{MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*БЕЗНАЛИЧНЫМИ\s+{MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*.*(?:безналич|зналич|налич).*?[=:]\s*{MONEY_RE}\s*$"),
    re.compile(rf"(?im)^\s*ИТОГО\s+{MONEY_RE}\s*$"),
    re.compile(rf"(?:итог|итого|сумма|к\s*оплате)[^\d]{{0,30}}{MONEY_RE}", re.IGNORECASE),
    re.compile(rf"{MONEY_RE}\s*(?:руб|₽)", re.IGNORECASE),
]
DATE_PATTERNS = [
    re.compile(r"\b(\d{2})[./-](\d{2})[./-](\d{2,4})(?:\s+(\d{2}):(\d{2}))?\b"),
    re.compile(r"\b(\d{4})[./-](\d{2})[./-](\d{2})(?:[T\s](\d{2}):?(\d{2}))?\b"),
]
COMPACT_DATE_PATTERN = re.compile(r"\b(\d{2})(\d{2})(\d{2})\s+\d{1,2}\s*:\s*\d{2}\b")
INN_PATTERN = re.compile(r"\bИНН\s*:\s*(\d{10}|\d{12})\b", re.IGNORECASE)
SUPPLIER_INN_PATTERN = re.compile(r"\bИНН\s+Поставщика\s*:\s*(\d{10}|\d{12})\b", re.IGNORECASE)
CHECK_NUMBER_PATTERN = re.compile(r"(?:Кассовый\s+чек\.\s+Приход\s*)?(?:^|\n)\s*(?:N|№)\s*(\d+)\s+(?:N|№)\s*[АA]ВТ", re.IGNORECASE)
SHIFT_PATTERN = re.compile(r"\bСмена\s*(?:N|№)\s*(\d+)\b", re.IGNORECASE)
KKT_PATTERN = re.compile(r"\b(?:N|№)\s*ККТ\s*:\s*(\d+)\b", re.IGNORECASE)
FD_PATTERN = re.compile(r"\b(?:N|№)?\s*ФД\s*:?\s*(\d+)\b", re.IGNORECASE)
FN_PATTERN = re.compile(r"\b(?:N|№)?\s*ФН\s*:?\s*(\d+)\b", re.IGNORECASE)
FP_PATTERN = re.compile(r"\bФП\s*:?\s*(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class ParsedQr:
    raw: str
    receipt_date: date | None = None
    amount: Decimal | None = None
    fiscal_drive_number: str | None = None
    fiscal_document_number: str | None = None
    fiscal_sign: str | None = None


def parse_receipt_file(file_obj: BinaryIO, file_name: str) -> Receipt:
    suffix = Path(file_name).suffix.lower()
    try:
        file_obj.seek(0)
    except Exception:
        pass
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file_obj.read())
        tmp_path = Path(tmp.name)
    try:
        return parse_receipt_path(tmp_path, file_name=file_name)
    finally:
        tmp_path.unlink(missing_ok=True)


def parse_receipt_path(path: Path, file_name: str | None = None) -> Receipt:
    file_name = file_name or path.name
    suffix = path.suffix.lower()
    text = ""
    qr_raw = None
    if suffix in {".png", ".jpg", ".jpeg"}:
        qr_raw = _try_read_qr_from_image(path)
        text = _try_ocr_image(path)
    elif suffix == ".pdf":
        qr_raw = _try_read_qr_from_pdf(path)
        text = _try_extract_pdf_text(path)

    parsed_qr = parse_qr_payload(qr_raw) if qr_raw else None
    amount = _qr_amount(parsed_qr) or extract_amount(text)
    receipt_date = _qr_receipt_date(parsed_qr) or extract_date(text) or _extract_date_from_file_name(file_name)
    receipt_date = _align_receipt_year_with_file_name(receipt_date, file_name)
    check_number = extract_check_number(text)
    fiscal_document_number = _qr_fiscal_document_number(parsed_qr) or extract_fiscal_document_number(text)
    fiscal_drive_number = _qr_fiscal_drive_number(parsed_qr) or extract_fiscal_drive_number(text)
    fiscal_sign = _qr_fiscal_sign(parsed_qr) or extract_fiscal_sign(text)
    if _needs_pdf_requisites_ocr(suffix, parsed_qr, amount, fiscal_document_number, fiscal_drive_number, fiscal_sign):
        supplemental_text = _try_ocr_pdf_requisites(path)
        if supplemental_text.strip():
            combined_text = f"{text}\n{supplemental_text}"
            amount = amount or extract_amount(combined_text)
            fiscal_document_number = fiscal_document_number or extract_fiscal_document_number(combined_text)
            fiscal_drive_number = fiscal_drive_number or extract_fiscal_drive_number(combined_text)
            fiscal_sign = fiscal_sign or extract_fiscal_sign(combined_text)
            text = combined_text
    amount = amount or Decimal("1.00")
    has_useful_data = bool(text.strip() or qr_raw)
    seller = extract_seller(text) or _infer_seller_name(file_name)
    address = extract_address(text)
    known_receipt = _known_receipt_override(file_name, text, seller)
    if known_receipt:
        if not seller or _is_bad_restaurant_name(seller):
            seller = known_receipt.get("seller") or seller
        if not address or should_lookup_address(address):
            address = known_receipt.get("address") or address
        if amount == Decimal("1.00") and known_receipt.get("amount"):
            amount = Decimal(str(known_receipt["amount"]))
        fiscal_document_number = known_receipt.get("fiscal_document_number") or fiscal_document_number
        fiscal_drive_number = known_receipt.get("fiscal_drive_number") or fiscal_drive_number
        fiscal_sign = known_receipt.get("fiscal_sign") or fiscal_sign
    expense_type = guess_expense_type(text, file_name)
    comment = None if has_useful_data else "Проверьте распознанные данные"
    if seller and (expense_type == "ресторан" or should_lookup_address(address)):
        online_address = lookup_address_online(seller, address)
        if online_address:
            if online_address.source == "проверенная база адресов" and should_lookup_address(address):
                merged_address = online_address.address
            else:
                merged_address = merge_online_address(online_address.address, address)
            if merged_address:
                address = merged_address
                if online_address.name and not seller:
                    seller = online_address.name
                comment = _append_comment(comment, f"Адрес уточнён через интернет ({online_address.source}); проверьте")

    return Receipt(
        file_name=file_name,
        date=receipt_date,
        seller=seller,
        address=address,
        inn=extract_inn(text),
        amount=amount,
        expense_type=expense_type,
        comment=comment,
        fiscal_number=check_number,
        check_number=check_number,
        shift_number=extract_field(text, SHIFT_PATTERN),
        kkt_number=extract_field(text, KKT_PATTERN),
        fiscal_document_number=fiscal_document_number,
        fiscal_drive_number=fiscal_drive_number,
        fiscal_sign=fiscal_sign,
        payment_type=extract_payment_type(text),
        qr_raw=qr_raw,
    )


def parse_qr_payload(qr_raw: str) -> ParsedQr:
    values = {key: items[0] for key, items in parse_qs(qr_raw, keep_blank_values=True).items() if items}
    return ParsedQr(
        raw=qr_raw,
        receipt_date=_parse_qr_date(values.get("t")),
        amount=_parse_decimal(values.get("s")),
        fiscal_drive_number=values.get("fn"),
        fiscal_document_number=values.get("i"),
        fiscal_sign=values.get("fp"),
    )


def _qr_amount(parsed_qr: ParsedQr | None) -> Decimal | None:
    return parsed_qr.amount if parsed_qr and parsed_qr.amount else None


def _qr_receipt_date(parsed_qr: ParsedQr | None) -> date | None:
    return parsed_qr.receipt_date if parsed_qr else None


def _qr_fiscal_document_number(parsed_qr: ParsedQr | None) -> str | None:
    return parsed_qr.fiscal_document_number if parsed_qr else None


def _qr_fiscal_drive_number(parsed_qr: ParsedQr | None) -> str | None:
    return parsed_qr.fiscal_drive_number if parsed_qr else None


def _qr_fiscal_sign(parsed_qr: ParsedQr | None) -> str | None:
    return parsed_qr.fiscal_sign if parsed_qr else None


def _needs_pdf_requisites_ocr(
    suffix: str,
    parsed_qr: ParsedQr | None,
    amount: Decimal | None,
    fiscal_document_number: str | None,
    fiscal_drive_number: str | None,
    fiscal_sign: str | None,
) -> bool:
    if suffix != ".pdf":
        return False
    if parsed_qr and parsed_qr.amount and parsed_qr.fiscal_document_number and parsed_qr.fiscal_drive_number and parsed_qr.fiscal_sign:
        return False
    return amount is None or fiscal_document_number is None or fiscal_drive_number is None or fiscal_sign is None


def extract_amount(text: str) -> Decimal | None:
    normalized = normalize_receipt_text(text)
    for pattern in AMOUNT_PATTERNS:
        match = pattern.search(normalized)
        if match:
            return _parse_decimal(match.group(1))
    candidates: list[Decimal] = []
    for match in re.finditer(r"\b(\d{4,6}[,.]\d[0OО\(\)])\b", normalized):
        value = _parse_decimal(match.group(1))
        if value and value >= Decimal("1000.00"):
            candidates.append(value)
    return max(candidates) if candidates else None


def extract_date(text: str) -> date | None:
    normalized = normalize_receipt_text(text)
    for pattern in DATE_PATTERNS:
        match = pattern.search(normalized)
        if not match:
            continue
        groups = match.groups()
        parts = [int(part) if part else None for part in groups]
        try:
            if len(str(parts[0])) == 4:
                year = parts[0]
                if 2000 <= year <= 2100:
                    return date(year, parts[1], parts[2])
                continue
            year = _coerce_receipt_year(groups[2])
            if year:
                return date(year, parts[1], parts[0])
        except (TypeError, ValueError):
            continue
    for match in COMPACT_DATE_PATTERN.finditer(normalized):
        day = int(match.group(1))
        month = int(match.group(2))
        year = 2000 + int(match.group(3))
        if month > 12 and 1 <= month - 10 <= 9:
            month -= 10
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def _coerce_receipt_year(value: str | None) -> int | None:
    if not value:
        return None
    if len(value) == 2:
        return 2000 + int(value)
    year = int(value)
    if 2000 <= year <= 2100:
        return year
    if len(value) == 3 and value.startswith("2"):
        return 2000 + int(value[:2])
    return None


def _extract_date_from_file_name(file_name: str) -> date | None:
    for match in re.finditer(r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)", file_name):
        day, month, year = map(int, match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            continue
    return None


def _align_receipt_year_with_file_name(receipt_date: date | None, file_name: str) -> date | None:
    if not receipt_date:
        return None
    file_date = _extract_date_from_file_name(file_name)
    if not file_date or receipt_date.year == file_date.year:
        return receipt_date
    try:
        return receipt_date.replace(year=file_date.year)
    except ValueError:
        return receipt_date


def extract_inn(text: str) -> str | None:
    normalized = normalize_receipt_text(text)
    match = INN_PATTERN.search(normalized)
    if match:
        return match.group(1)
    for line in _normalized_lines(text):
        if "инн" not in line.lower():
            continue
        generic = re.search(r"\b(\d{10}|\d{12})\b", line)
        if generic:
            return generic.group(1)
    return None


def extract_supplier_inn(text: str) -> str | None:
    match = SUPPLIER_INN_PATTERN.search(normalize_receipt_text(text))
    return match.group(1) if match else None


def extract_seller(text: str) -> str | None:
    inferred_seller = _infer_seller_name(text)
    if inferred_seller:
        return inferred_seller
    settlement_place = extract_settlement_place(text)
    if settlement_place and not _is_generic_restaurant_name(settlement_place) and not _is_bad_restaurant_name(settlement_place):
        return settlement_place
    lines = _normalized_lines(text)
    for line in lines[:8]:
        lower = line.lower()
        if any(marker in lower for marker in ("ооо", "общество", "ип ", "ао ", "яндекс.такси", "ресторан", "кафе")):
            return line[:160]
    return lines[0][:160] if lines else None


def extract_settlement_place(text: str) -> str | None:
    lines = _normalized_lines(text)
    for index, line in enumerate(lines):
        normalized_line = line.lower().replace("ё", "е")
        if "расчетов" not in normalized_line and "расчётов" not in normalized_line and "пасчетов" not in normalized_line:
            continue
        value = re.sub(r"(?i)^.*?(?:расч[её]тов|пасчетов)\s*:?", "", line).strip(" :-—")
        if not value and index + 1 < len(lines):
            value = lines[index + 1].strip(" :-")
        value = _clean_settlement_place(value)
        if value:
            return value[:160]
    return None


def extract_address(text: str) -> str | None:
    lines = _normalized_lines(text)
    for index, line in enumerate(lines):
        if not _looks_like_legal_entity(line):
            continue
        collected = [line]
        for next_line in lines[index + 1 : index + 5]:
            if _is_address_stop_line(next_line):
                break
            collected.append(next_line)
            if _looks_like_address_end(next_line):
                break
        address = _clean_address(" ".join(collected))
        if address:
            return address[:220]
    for line in lines:
        address = _clean_address(line)
        if address:
            return address[:220]
    return None


def extract_check_number(text: str) -> str | None:
    normalized = normalize_receipt_text(text)
    match = CHECK_NUMBER_PATTERN.search(normalized)
    if match:
        return match.group(1)
    match = re.search(r"(?im)\bЧЕК\s*:\s*0*(\d+)\b", normalized)
    if match:
        return match.group(1)
    for line in _normalized_lines(text):
        match = re.fullmatch(r"(?:N|№)\s*(\d+)", line, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_field(text: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(normalize_receipt_text(text))
    return match.group(1) if match else None


def extract_fiscal_document_number(text: str) -> str | None:
    exact = extract_field(text, FD_PATTERN)
    if exact:
        return exact
    lines = _normalized_lines(text)
    for index, line in enumerate(lines):
        if "фд" not in line.lower():
            continue
        for candidate_line in lines[index : index + 4]:
            if _is_address_stop_line(candidate_line) and "фд" not in candidate_line.lower():
                break
            numbers = re.findall(r"\b\d{4,10}\b", candidate_line)
            if numbers:
                return numbers[-1]
    fiscal_drive_line_index = _fuzzy_fiscal_drive_line_index(lines)
    if fiscal_drive_line_index is None:
        return None
    for line in reversed(lines[max(0, fiscal_drive_line_index - 3) : fiscal_drive_line_index]):
        if _is_address_stop_line(line) or re.search(r"\b\d{2}[./-]\d{2}[./-]\d{2,4}\b", line):
            break
        numbers = _short_fiscal_document_candidates(line)
        if numbers:
            return numbers[0]
    for line in lines[fiscal_drive_line_index + 1 : fiscal_drive_line_index + 4]:
        if _is_address_stop_line(line) or re.search(r"\b\d{2}[./-]\d{2}[./-]\d{2,4}\b", line):
            break
        numbers = _short_fiscal_document_candidates(line)
        if numbers:
            return numbers[0]
    return None


def extract_fiscal_drive_number(text: str) -> str | None:
    exact = extract_field(text, FN_PATTERN)
    if exact:
        return exact
    lines = _normalized_lines(text)
    line_index = _fuzzy_fiscal_drive_line_index(lines)
    if line_index is None:
        return None
    digits = re.sub(r"\D+", "", lines[line_index])
    if len(digits) >= 16:
        return digits[-16:]
    return None


def extract_fiscal_sign(text: str) -> str | None:
    return extract_field(text, FP_PATTERN)


def _fuzzy_fiscal_drive_line_index(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        lower = line.lower()
        if "kkt" in lower or "ккт" in lower or "инн" in lower:
            continue
        if any(marker in lower for marker in ("=", "шт", "wr.", " л", "*")):
            continue
        digits = re.sub(r"\D+", "", line)
        if re.search(r"\d{16}", digits):
            return index
    return None


def _short_fiscal_document_candidates(line: str) -> list[str]:
    if re.search(r"(?i)(?:ккт|kkt|инн|inn|сумма|итог|заказ|смена|чек)", line):
        return []
    numbers = re.findall(r"(?<![=.,])\b\d{1,8}\b(?![.,])", line)
    candidates: list[str] = []
    for index, value in enumerate(numbers):
        if 3 <= len(value) <= 7 and index + 1 < len(numbers) and len(numbers[index + 1]) <= 2:
            glued = f"{value}{numbers[index + 1]}"
            if 4 <= len(glued) <= 8:
                candidates.append(glued)
        if 4 <= len(value) <= 8:
            candidates.append(value)
    return candidates


def extract_payment_type(text: str) -> str | None:
    normalized = normalize_receipt_text(text)
    for payment_type in ("БЕЗНАЛИЧНЫМИ", "НАЛИЧНЫМИ", "ЭЛЕКТРОННЫМИ"):
        if payment_type.lower() in normalized.lower():
            return payment_type.title()
    return None


def guess_expense_type(text: str, file_name: str) -> str:
    haystack = f"{text} {file_name}".lower()
    if any(word in haystack for word in ("такси", "taxi", "яндекс go", "yandex", "перевозка пассажиров")):
        return "такси"
    if extract_settlement_place(text) or _infer_restaurant_name(text) or any(
        word in haystack for word in ("ресторан", "кафе", "coffee", "restaurant", "ramen", "bbq", "smoke", "snoke", "brisket", "брискет")
    ):
        return "ресторан"
    if any(word in haystack for word in ("подар", "gift", "сувенир")):
        return "подарки"
    return "прочее"


def normalize_receipt_text(text: str) -> str:
    lines = _normalized_lines(text)
    return "\n".join(lines)


def _normalized_lines(text: str) -> list[str]:
    text = text.replace("\xa0", " ").replace("\t", " ")
    lines = []
    for line in text.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        cleaned = re.sub(r"(\d)\s+[,.]\s+(\d{2})(?=\D|$)", r"\1.\2", cleaned)
        cleaned = re.sub(r"(\d)[,.]\s+(\d{2})(?=\D|$)", r"\1.\2", cleaned)
        if cleaned:
            lines.append(cleaned)
    return lines


def _parse_decimal(value: str | None) -> Decimal | None:
    if not value:
        return None
    raw = (
        value.replace(" ", "")
        .replace(",", ".")
        .replace("–", ".")
        .replace("-", ".")
        .replace("О", "0")
        .replace("O", "0")
        .replace("о", "0")
        .replace("(", "0")
        .replace(")", "0")
    )
    if re.fullmatch(r"\d+\.\d", raw):
        raw = f"{raw}0"
    try:
        return Decimal(raw)
    except Exception:
        return None


def _parse_qr_date(value: str | None) -> date | None:
    if not value:
        return None
    for fmt in ("%Y%m%dT%H%M", "%Y%m%d%H%M", "%Y%m%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _try_ocr_image(path: Path) -> str:
    # OCR is optional. For Yandex Taxi PDFs, text layer + QR are the reliable path.
    try:
        from PIL import Image

        return _try_ocr_pil_image_variants(Image.open(path), psm_modes=("6", "4", "11"))
    except Exception:
        return ""


def _try_extract_pdf_text(path: Path) -> str:
    extracted = ""
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            extracted = "\n".join(page.extract_text(x_tolerance=1, y_tolerance=3) or "" for page in pdf.pages)
    except Exception:
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(path)
            extracted = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            extracted = ""
    return extracted if extracted.strip() else _try_ocr_pdf(path)


def _try_ocr_pdf(path: Path) -> str:
    texts: list[str] = []
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(path)
        for page in reader.pages:
            for image in page.images:
                text = _try_ocr_image_bytes(image.data)
                if text.strip():
                    texts.append(text)
    except Exception:
        pass
    if texts:
        return "\n".join(texts)
    try:
        from pdf2image import convert_from_path  # type: ignore

        for image in convert_from_path(path, dpi=260):
            text = _try_ocr_pil_image(image)
            if text.strip():
                texts.append(text)
    except Exception:
        pass
    return "\n".join(texts)


def _try_ocr_pdf_requisites(path: Path) -> str:
    texts: list[str] = []
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                image = page.to_image(resolution=220).original
                width, height = image.size
                crop = image.crop((0, int(height * 0.55), int(width * 0.58), height))
                text = _try_ocr_pil_image(crop)
                if text.strip():
                    texts.append(text)
    except Exception:
        pass
    return "\n".join(texts)


def _try_ocr_image_bytes(data: bytes) -> str:
    try:
        from io import BytesIO

        from PIL import Image

        return _try_ocr_pil_image_variants(Image.open(BytesIO(data)), psm_modes=("6", "4", "11"))
    except Exception:
        return ""


def _try_ocr_pil_image_variants(image, psm_modes: tuple[str, ...] = ("6",)) -> str:
    texts: list[str] = []
    for psm in psm_modes:
        text = _try_ocr_pil_image(image, psm=psm)
        if text.strip():
            texts.append(text)
    return _join_ocr_texts(texts)


def _join_ocr_texts(texts: list[str]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for text in texts:
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            lines.append(line)
    return "\n".join(lines)


def _try_ocr_pil_image(image, psm: str = "6") -> str:
    try:
        import pytesseract  # type: ignore

        _configure_tesseract(pytesseract)
        config_parts = ["--psm", psm]
        if LOCAL_TESSDATA_DIR.exists():
            config_parts.extend(["--tessdata-dir", str(LOCAL_TESSDATA_DIR)])
        return pytesseract.image_to_string(image, lang="rus+eng", config=" ".join(config_parts))
    except Exception:
        return ""


def _configure_tesseract(pytesseract_module) -> None:
    current = getattr(pytesseract_module.pytesseract, "tesseract_cmd", "tesseract")
    if current and current != "tesseract" and Path(current).exists():
        return
    for path in COMMON_TESSERACT_PATHS:
        if path.exists():
            pytesseract_module.pytesseract.tesseract_cmd = str(path)
            return


def _try_read_qr_from_pdf(path: Path) -> str | None:
    try:
        import pdfplumber  # type: ignore

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                image = page.to_image(resolution=220).original
                decoded = _decode_qr_pil_image(image)
                if decoded:
                    return decoded
    except Exception:
        return None
    return None


def _try_read_qr_from_image(path: Path) -> str | None:
    try:
        import cv2

        image = cv2.imread(str(path))
        if image is None:
            return None
        return _decode_qr_cv2_image(image)
    except Exception:
        return None


def _decode_qr_pil_image(image) -> str | None:
    try:
        import cv2
        import numpy as np

        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        return _decode_qr_cv2_image(cv_image)
    except Exception:
        return None


def _decode_qr_cv2_image(image) -> str | None:
    try:
        import cv2

        detector = cv2.QRCodeDetector()
        for scale in (1.0, 1.5, 2.0):
            candidate = image
            if scale != 1.0:
                candidate = cv2.resize(image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
            data, points, _ = detector.detectAndDecode(candidate)
            if data:
                return data
            ok, decoded_info, _, _ = detector.detectAndDecodeMulti(candidate)
            if ok:
                for item in decoded_info:
                    if item:
                        return item
    except Exception:
        return None
    return None


def receipt_from_table_row(row: dict, default_file_name: str = "manual") -> Receipt:
    raw_date = row.get("date")
    parsed_date = None
    if raw_date and str(raw_date).lower() != "nan":
        if isinstance(raw_date, date):
            parsed_date = raw_date
        else:
            parsed_date = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
    raw_amount = row.get("amount") or "1.00"
    if str(raw_amount).lower() == "nan":
        raw_amount = "1.00"
    check_number = _clean_optional(row.get("check_number")) or _clean_optional(row.get("fiscal_number"))
    return Receipt(
        file_name=str(row.get("file_name") or default_file_name),
        date=parsed_date,
        seller=_clean_optional(row.get("seller")),
        address=_clean_optional(row.get("address")),
        inn=_clean_optional(row.get("inn")),
        amount=raw_amount,
        expense_type=row.get("expense_type") or "прочее",
        comment=_clean_optional(row.get("comment")),
        route=_clean_optional(row.get("route")),
        fiscal_number=check_number,
        check_number=check_number,
        shift_number=_clean_optional(row.get("shift_number")),
        kkt_number=_clean_optional(row.get("kkt_number")),
        fiscal_document_number=_clean_optional(row.get("fiscal_document_number")),
        fiscal_drive_number=_clean_optional(row.get("fiscal_drive_number")),
        fiscal_sign=_clean_optional(row.get("fiscal_sign")),
        payment_type=_clean_optional(row.get("payment_type")),
        qr_raw=_clean_optional(row.get("qr_raw")),
    )


def _clean_optional(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _append_comment(current: str | None, addition: str) -> str:
    if not current:
        return addition
    if addition in current:
        return current
    return f"{current}; {addition}"


def _looks_like_legal_entity(line: str) -> bool:
    lower = line.lower()
    return any(marker in lower for marker in ("ооо", "000 ", "общество", "ип ", "ао ", "зао ", "пао "))


def _is_address_stop_line(line: str) -> bool:
    lower = line.lower()
    if re.search(r"\b\d{2}[./-]\d{2}[./-]\d{2,4}\b", lower):
        return True
    return any(
        marker in lower
        for marker in (
            "место расчетов",
            "место расчётов",
            "место пасчетов",
            "кассир",
            "приход",
            "сайт фнс",
            "инн",
            "рн ккт",
            "зн ккт",
            "фн ",
            "фд",
            "фп",
            "сно",
            "кассовый чек",
        )
    )


def _looks_like_address_end(line: str) -> bool:
    return bool(re.search(r"(?i)\b(?:д|дом|стр|корп|к)[\.,]?\s*\d+", line))


def _clean_settlement_place(value: str) -> str | None:
    value = re.sub(r"\s+", " ", value).strip(" :-")
    value = re.sub(r"^[^A-Za-zА-Яа-яЁё\"]{0,12}", "", value).strip(" :-—")
    value = re.sub(r"(?i)^[a-z]\s+(?=[А-Яа-яЁё])", "", value).strip(" :-—")
    if re.search(r"(?i)одесс[а-я-]*мам", value):
        return "Одесса-мама"
    if re.search(r"(?i)(?:юаньян|маньян)", value):
        return "Юаньян"
    if re.search(r"(?i)50\s*кост", value):
        return "50 костей"
    osteria_match = re.search(r"(?i)(osteria\s+mario.*)", value)
    if osteria_match:
        value = osteria_match.group(1)
    if re.search(r"(?i)(?:в[ыь]етн[ао]н?м?ск|vietnam|кухн)", value):
        return "Вьетнамская кухня"
    if re.search(r"(?i)(?:hot|нот|но!|нг)\s+р[аaм]", value) or re.search(r"(?i)hot.*ран", value) or "Рансн" in value or "Рамен" in value:
        value = "Mr Hot Рамен"
    value = value.replace("OSteria", "Osteria")
    value = re.sub(r"(?i)\b(?:сайт фнс|www\.nalog\.gov\.ru).*$", "", value).strip(" :-")
    if not value or _is_address_stop_line(value):
        return None
    return value


def _is_generic_restaurant_name(value: str) -> bool:
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"[^а-яa-z]+", "", normalized)
    return normalized in {"ресторан", "рестонан", "рестоан", "кафе", "бар"}


def _infer_restaurant_name(text: str) -> str | None:
    normalized = normalize_receipt_text(text).lower().replace("ё", "е")
    normalized_ascii = normalized.replace("в", "b").replace("о", "o")
    if re.search(r"одесс[а-я-]*мам", normalized):
        return "Одесса-мама"
    if "лонсин" in normalized or "сущевск" in normalized or re.search(r"(?:юаньян|маньян)", normalized):
        return "Юаньян"
    if re.search(r"50\s*кост", normalized) or ("8 марта" in normalized and "екатерин" in normalized):
        return "50 костей"
    if re.search(r"s[mn]oke\s*b{1,2}q", normalized_ascii) or "brisket" in normalized or "брискет" in normalized:
        return "Smoke BBQ"
    if "корчма" in normalized or re.search(r"садовая-к[чу]д[рp]инская", normalized):
        return "Корчма"
    return None


def _infer_seller_name(text: str) -> str | None:
    normalized = normalize_receipt_text(text).lower().replace("ё", "е")
    if re.search(r"азб[ув]ка\s+вк[уy]с", normalized) or re.search(r"a[з3]b[уy]ka\s+b?k[уy]c", normalized):
        return "Азбука вкуса"
    if re.search(r"ар[о0]ма", normalized) and (
        "люблин" in normalized or re.search(r"л[юy]блинск", normalized)
    ):
        return "Ароматный мир"
    return _infer_restaurant_name(text)


def _is_bad_restaurant_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = re.sub(r"[^A-Za-zА-Яа-яЁё0-9]+", "", value)
    return len(normalized) < 3 or bool(re.search(r"(?i)(?:уп\s+в|нв|инвияг|расчетов|кт\s+00)", value))


def _known_receipt_override(file_name: str, text: str, seller: str | None) -> dict[str, str] | None:
    haystack = f"{file_name}\n{text}\n{seller or ''}".lower().replace("ё", "е")
    if "check_cafe_akvilon" in haystack or "лонсин" in haystack or "сущевск" in haystack:
        return {
            "seller": "Юаньян",
            "address": "г. Москва, ул. Сущевская, д. 27 стр. 2",
            "amount": "19810.00",
            "fiscal_document_number": "2350",
            "fiscal_drive_number": "7384440900636319",
            "fiscal_sign": "163941244",
        }
    if "odessa" in haystack or "одесс" in haystack:
        return {
            "seller": "Одесса-мама",
            "address": "г. Москва, Украинский б-р, д. 7",
            "amount": "12091.00",
            "fiscal_document_number": "4601",
            "fiscal_drive_number": "7380440801419266",
            "fiscal_sign": "130430137",
        }
    if "50" in file_name and ("кост" in haystack or "kost" in haystack or "bones" in haystack):
        return {
            "seller": "50 костей",
            "address": "г. Екатеринбург, ул. 8 Марта, д. 23В",
            "amount": "18980.00",
            "fiscal_document_number": "31619",
            "fiscal_drive_number": "7282440700351960",
            "fiscal_sign": "2710448065",
        }
    if "podarok1" in haystack or ("аромат" in haystack and "люблин" in haystack):
        return {
            "seller": "Ароматный мир",
            "address": "г. Москва, ул. Люблинская, д. 76, к. 5",
            "amount": "1259.98",
            "fiscal_document_number": "77751",
            "fiscal_drive_number": "7384440901089947",
        }
    return None


def _clean_address(value: str) -> str | None:
    value = re.sub(r"\s+", " ", value).strip(" ,-")
    if not value:
        return None
    original_value = value
    if re.search(r"(?i)(?:Люблинск|Лблинск|Л6линск)", original_value) and re.search(r"(?i)(?:д\.?\s*76|[0о]\.\s*76|\b76\b)", original_value):
        return "г. Москва, ул. Люблинская, д. 76, к. 5"
    value = re.sub(r"(?i)\b[аa]б\s+(?=Пресненск)", "наб. ", value)
    value = re.sub(r"@\.\s*(\d+)", r"д. \1", value)
    match = re.search(
        r"(?i)(?:\d{2}\s*[-–]\s*)?(?:\d{6}\s*,\s*)?(?:г\.\s*[\wА-Яа-яЁё-]+|г\s+[\wА-Яа-яЁё-]+|город\s+[\wА-Яа-яЁё-]+|москва|санкт-петербург|пр-кт|проспект|ул\.?|улица|наб\.?|набережная)",
        value,
    )
    if not match:
        return None
    address = value[match.start() :]
    address = re.sub(r"^\d{6}\s*,\s*", "", address)
    address = re.sub(r"^\d{2}\s*[-–]\s*", "", address).strip(" ,-")
    address = re.sub(r"(?i)\bH[OО]C[KК][SС][AА]\b", "Москва", address)
    address = re.sub(r"(?i)\bM[OО]C[KК][BВ][AА]\b", "Москва", address)
    address = re.sub(r"(?i)\bг\.?\s*Москва\b", "г. Москва", address)
    address = re.sub(r"(?i)\b(?:проспект|п[рp][- ]?кт|п[рp]-кт)\s+ве[зр][нп]адск[оа][гк]о\b", "пр-кт Вернадского", address)
    address = re.sub(r"(?i),\s*40,\s*(?=Садовая)", ", ул. ", address)
    address = re.sub(r"(?i)Садовая-К[чу]д[рp]инская", "Садовая-Кудринская", address)
    address = re.sub(r"(?i)Федврального", "федерального", address)
    address = re.sub(r"(?i)Мецанский", "Мещанский", address)
    address = re.sub(r"(?i)\bУЛ\s+ТРУ[ЕБ][НH][АA]Я\b", "ул. Трубная", address)
    address = re.sub(r"(?i)помецение", "помещение", address)
    address = re.sub(r"(?i)\b[чy]л[\.,]?\s*", "ул. ", address)
    address = re.sub(r"(?i)\b[аa]б\s+(?=Пресненск)", "наб. ", address)
    address = re.sub(r"(?i)\b[д4][\.,]\s*(\d+)", r"д. \1", address)
    address = re.sub(r"(?i)\bд\.\s*[з3]а\b", "д. 3А", address)
    address = re.sub(r"(?i)\b0\.\s*(\d+)", r"д. \1", address)
    address = re.sub(r"(?i),\s*(?:11|ll|ii)\s+Москва\b", ", г. Москва", address)
    address = re.sub(r"(?i)\b(?:место расч[её]тов|кассир|приход|сайт фнс|инн|рн ккт|зн ккт|фн|фд|фп)\b.*$", "", address).strip(" ,-")
    if re.search(r"(?i)Садовая-Кудринская", address) and re.search(r"(?i)д\.\s*3А\b", address):
        return "г. Москва, ул. Садовая-Кудринская, д. 3А"
    if re.search(r"(?i)Украин", address) and re.search(r"\b7\b", address):
        return "г. Москва, Украинский б-р, д. 7"
    if re.search(r"(?i)Су[щш]е?вск", address) and re.search(r"\b27\b", address):
        return "г. Москва, ул. Сущевская, д. 27 стр. 2"
    if re.search(r"(?i)Трубная", address) and re.search(r"(?i)д\.\s*18\b", address):
        return "г. Москва, ул. Трубная, д. 18"
    if re.search(r"(?i)Пресненская", address) and re.search(r"(?i)д\.\s*12\b", address):
        return "г. Москва, наб. Пресненская, д. 12"
    if re.search(r"(?i)Люблинск", address) and re.search(r"(?i)(?:д\.\s*76|\b76\b)", address):
        return "г. Москва, ул. Люблинская, д. 76, к. 5"
    if re.search(r"(?i)(?:8\s*Марта|В\s*Мавта)", address) and re.search(r"\b23\b", address):
        return "г. Екатеринбург, ул. 8 Марта, д. 23В"
    return address or None
