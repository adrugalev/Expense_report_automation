from datetime import date

import pytest

from src.models import Employee, Receipt, RepresentativeExpenseReport
from src.text_normalization import capitalize_first, normalize_address_case


def test_capitalize_first():
    assert capitalize_first("менеджер по продажам") == "Менеджер по продажам"
    assert capitalize_first("Руководитель направления продаж") == "Руководитель направления продаж"
    assert capitalize_first("") == ""


@pytest.mark.parametrize(("value", "expected"), [
    (None, None),
    ("", ""),
    ("г. Москва. мунициПАльный округ ТВеРсКОЙ. Ул. 1-я ТверскАя-ЯмсКАя. д. 16/23. стр. 1",
     "г. Москва. муниципальный округ Тверской. ул. 1-я Тверская-Ямская. д. 16/23. стр. 1"),
    ("Г. КАЗАНЬ, УЛ. ПЕРВАЯ-ГОРОДСКАЯ, Д. 7, СТР. 2", "г. Казань, ул. Первая-Городская, д. 7, стр. 2"),
    ("г. Москва, ул. Земляной Вал, д. 9А", "г. Москва, ул. Земляной Вал, д. 9А"),
    ("г. Ростов-на-Дону, ул. 1-Я Линия, д. 12Б/3, к1", "г. Ростов-на-Дону, ул. 1-я Линия, д. 12Б/3, к1"),
    ("СПб, СНТ Восход, ЖК ВДНХ, ЦАО, д. 8А", "СПб, СНТ Восход, ЖК ВДНХ, ЦАО, д. 8А"),
    ("г. Москва, ТЦ iCity, ул. 8 Марта, д. 23В", "г. Москва, ТЦ iCity, ул. 8 Марта, д. 23В"),
    ("офис компании Huaxun", "офис компании Huaxun"),
])
def test_address_case_normalization_preserves_address_details(value, expected):
    assert normalize_address_case(value) == expected
    assert normalize_address_case(normalize_address_case(value)) == expected


def test_receipt_normalizes_old_or_manually_supplied_address():
    receipt = Receipt(file_name="scan.pdf", amount="10123.50", address="г. Москва, УЛ. ТверскАя-ЯмсКАя, Д. 16/23")

    assert receipt.address == "г. Москва, ул. Тверская-Ямская, д. 16/23"


def test_report_normalizes_old_meeting_place_without_receipt_address():
    report = RepresentativeExpenseReport(
        initiator=Employee(full_name="Иванов Иван", position="Менеджер"),
        event_date=date(2026, 10, 18), report_date=date(2026, 10, 18),
        place="г. Москва, УЛ. ТверскАя-ЯмсКАя, Д. 16/23",
        restaurant_name="Гамбринус", counterparty="ANTTEQ",
        meeting_purpose="Обсуждение СОФ", meeting_result="Согласованы сроки",
    )

    assert report.place == "г. Москва, ул. Тверская-Ямская, д. 16/23"
