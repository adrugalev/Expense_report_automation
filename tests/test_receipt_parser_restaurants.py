from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.receipt_parser import (
    extract_amount,
    extract_address,
    extract_date,
    extract_fiscal_document_number,
    extract_fiscal_drive_number,
    extract_inn,
    extract_seller,
    guess_expense_type,
    receipt_from_table_row,
)


LOCAL_SCAN_DIR = Path("C:/Users/Drugalev/Dropbox/Сканы")


def test_extract_restaurant_name_and_address_from_ooo_receipt_text():
    text = """
    ООО "ЧОКИ"
    77 - г. Москва, вн. тер. г. муниципальный округ Донской, 115419,
    ул. Вавилова, д. 1
    Кассир Ким Вадим
    Место расчетов: Ресторан "КОРЁ"
    ИНН:9709058310
    """

    assert extract_seller(text) == 'Ресторан "КОРЁ"'
    assert extract_address(text) == "г. Москва, вн. тер. г. муниципальный округ Донской, 115419, ул. Вавилова, д. 1"
    assert guess_expense_type(text, "check7_3360.pdf") == "ресторан"


def test_extract_restaurant_name_and_address_from_ip_receipt_text():
    text = """
    МЕСТО РАСЧЕТОВ Mr Hot Рамен
    ИП ЛИ ЕБО 123112, г Москва, вн.тер.г. муниципальный
    округ Пресненский, наб Пресненская, д. 10
    02.02.26 13:40
    КАССИР ЛИ ЕБО
    """

    assert extract_seller(text) == "Mr Hot Рамен"
    assert extract_address(text) == "г. Москва, вн.тер.г. муниципальный округ Пресненский, наб Пресненская, д. 10"


def test_extract_vietnamese_kitchen_receipt_with_noisy_ocr_text():
    text = """
    oL ЗНАЛИЧНЫМИ | =2880.00
    Кассия ; Пе Каб КИ
    ИП ЛЕ КА КИ f
    123112, аб Пресненская, @. 12,11 Москва
    Место пасчетов f Выетнанская кухнЯ
    Зн KKT 0010572592129 R LR С
    РН KKT 00061 32354090321
    ИНН 71994092282
    % 730044 0902740399
    ® 10497 ‚д Оа
    """

    assert extract_seller(text) == "Вьетнамская кухня"
    assert extract_address(text) == "г. Москва, наб. Пресненская, д. 12"
    assert extract_amount(text) == Decimal("2880.00")
    assert extract_date(text + "\n091426 18: 42") == date(2026, 4, 9)
    assert extract_fiscal_drive_number(text) == "7300440902740399"
    assert extract_fiscal_document_number(text) == "10497"
    assert extract_inn(text) is None
    assert guess_expense_type(text, "check3_2880.pdf") == "ресторан"


def test_extract_korchma_receipt_with_noisy_ocr_text():
    text = """
    Кассовый чек
    Фирменный борц "КоРчма" — 530.00 %2 шт. =1060.00
    ИТОГ =21990.00
    БЕЗНАЛИЧНЫМИ =21990.00
    КассиР Гичык Елена
    000 "300-pynn”
    123242, г.Москва, 40, Садовая-КчдРинская, д. ЗА
    Место Расчетов Рестонан
    P KKT 0008761905043029
    ИНН 9703192704
    ФД ас e e
    1 17419203 O
    """

    assert extract_seller(text) == "Корчма"
    assert extract_address(text) == "г. Москва, ул. Садовая-Кудринская, д. 3А"
    assert extract_amount(text) == Decimal("21990.00")
    assert extract_fiscal_document_number(text) == "17419203"
    assert guess_expense_type(text, "check_cafe_corporative.pdf") == "ресторан"


def test_extract_smoke_bbq_receipt_with_noisy_ocr_text():
    text = """
    МОСКВА — — —
    SMOKE ВВО
    BAP'I'PUJIb ' KOTITWJ/IbHA
    Кассовый 4ex
    БРИсКет ДВОЙНОЙ 1 ПОРЦ. 3910.00*1 — шт. =3910.00
    wiorr _ =19109.00
    БЕЗНАЛИЧНЫМИ =19109.00
    ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "БРИСКЕТ"
    77 - город Федврального значения Москва, BH.TEP.T. МУНИЦИПЯЛЬНЫЙ
    ОКРУГ Мецанский,107045, ››› УЛ ТРУЕНаЯ, д. 18, помецение 1,
    НЕСТО РЯСЧеТОВ _ Snoke В80
    ИНН 7802692084
    OH 7380440801 836419
    0 47280 л Ь
    05.03.26 15:22
    """

    assert extract_seller(text) == "Smoke BBQ"
    assert extract_address(text) == "г. Москва, ул. Трубная, д. 18"
    assert extract_fiscal_document_number(text) == "47280"
    assert extract_date(text) == date(2026, 3, 5)
    assert guess_expense_type(text, "check_cafe_smokebbq.pdf") == "ресторан"


def test_extract_azbuka_vkusa_seller_from_noisy_ocr_text():
    text = """
    @&) азбука вкуса
    000 "ГОРОДСКОЙ СУПЕРМАРКЕТ"
    109369, Г. МОСКВА, УЛ. ЛЮБЛИНСКАЯ, Д. 96
    МЕСТО РАСЧЕТОВ СУПЕРМАРКЕТ "АЗВУКА BKYC .';Ё‘%Ъ‚
    """

    assert extract_seller(text) == "Азбука вкуса"


def test_extract_aromatny_mir_gift_receipt_from_noisy_ocr_text():
    text = """
    000 «АРона НФЁЁТ›
    109382, , МОСкба, _ Люблинская ул. , 0.76) K.5
    IECTG РАСЧЕТОВ М&Е "Ароматный
    АДР. ПОКУПАТЕ/Я adrugalevdgmail.com
    """

    assert extract_seller(text) == "Ароматный мир"
    assert extract_address(text) == "г. Москва, ул. Люблинская, д. 76, к. 5"


def test_extract_fiscal_document_number_before_fiscal_drive_line():
    text = """
    HECTO РАСЧЕТОВ МГ Hot Рамен
    ИП M E60 123112, Г Носква. ВН.тер.Г. МУНИЦИПальны
    Й ОКРУГ ПРесненский, Hdb Пресненская, 4. 10
    20.04.26 13:05 | KACCOBMM ЧЕК
    ИНН 280129593508
    Эн KK1 0444490042017828
    vl 2499 1 ЗЙ ЕНа
    01 2117552145 — ЗЕАа
    9Н 7364440900633551
    эн KKT 0009221134060839
    """

    assert extract_fiscal_document_number(text) == "24991"


def test_extract_amount_and_fiscal_document_from_requisites_ocr_text():
    text = """
    UTOIr _ 1728 -00
    CUMMa BES HOC 1728.00
    HECTO PACYETOB Hr HOt Pamen
    HHH 280129593508
    3H KKT 04444900420 1782
    A: 26132
    WN 4048787786
    WH 738444090063359 1
    PH KKT 000922 1134060835
    """

    assert extract_amount(text) == Decimal("1728.00")
    assert extract_fiscal_document_number(text) == "26132"
    assert extract_fiscal_drive_number(text) == "7384440900633591"


def test_extract_fiscal_drive_number_ignores_leading_ocr_digit():
    text = """
    9Н 7364440900633551
    """

    assert extract_fiscal_drive_number(text) == "7364440900633551"


def test_receipt_from_table_row_preserves_address():
    receipt = receipt_from_table_row(
        {
            "file_name": "check.pdf",
            "amount": "1030.00",
            "seller": "Mr Hot Рамен",
            "address": "г Москва, наб Пресненская, д. 10",
            "expense_type": "ресторан",
        }
    )

    assert receipt.amount == Decimal("1030.00")
    assert receipt.seller == "Mr Hot Рамен"
    assert receipt.address == "г Москва, наб Пресненская, д. 10"


@pytest.mark.skipif(
    not (LOCAL_SCAN_DIR / "check_cafe_akvilon.pdf").exists(),
    reason="local restaurant receipt fixture is unavailable",
)
def test_parse_akvilon_restaurant_receipt_pdf():
    from src.receipt_parser import parse_receipt_path

    receipt = parse_receipt_path(LOCAL_SCAN_DIR / "check_cafe_akvilon.pdf")

    assert receipt.seller == "Юаньян"
    assert receipt.address == "г. Москва, ул. Сущевская, д. 27 стр. 2"
    assert receipt.date == date(2025, 10, 23)
    assert receipt.amount == Decimal("19810.00")
    assert receipt.fiscal_document_number == "2350"


@pytest.mark.skipif(
    not (LOCAL_SCAN_DIR / "check_odessa_cafe_30062025.pdf").exists(),
    reason="local restaurant receipt fixture is unavailable",
)
def test_parse_odessa_mama_receipt_pdf():
    from src.receipt_parser import parse_receipt_path

    receipt = parse_receipt_path(LOCAL_SCAN_DIR / "check_odessa_cafe_30062025.pdf")

    assert receipt.seller == "Одесса-мама"
    assert receipt.address == "г. Москва, Украинский б-р, д. 7"
    assert receipt.date == date(2025, 6, 19)
    assert receipt.amount == Decimal("12091.00")
    assert receipt.fiscal_document_number == "4601"


@pytest.mark.skipif(
    not (LOCAL_SCAN_DIR / "Чек_50костей_02102024.pdf").exists(),
    reason="local restaurant receipt fixture is unavailable",
)
def test_parse_50_kostey_receipt_pdf():
    from src.receipt_parser import parse_receipt_path

    receipt = parse_receipt_path(LOCAL_SCAN_DIR / "Чек_50костей_02102024.pdf")

    assert receipt.seller == "50 костей"
    assert receipt.address == "г. Екатеринбург, ул. 8 Марта, д. 23В"
    assert receipt.date == date(2024, 10, 2)
    assert receipt.amount == Decimal("18980.00")
    assert receipt.fiscal_document_number == "31619"
