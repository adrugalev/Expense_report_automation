from datetime import date
from decimal import Decimal

from src.formatters import amount_to_words_ru, format_date_ru, format_rubles


def test_format_rubles_with_kopecks():
    assert format_rubles(Decimal("12450")) == "12 450,00 ₽"


def test_format_rubles_without_kopecks():
    assert format_rubles(Decimal("12450.40"), with_kopecks=False) == "12 450 ₽"


def test_amount_to_words_ru():
    result = amount_to_words_ru(Decimal("21.05"))
    assert "рубль" in result
    assert "05 копеек" in result


def test_format_date_ru():
    assert format_date_ru(date(2026, 6, 25)) == "25 июня 2026 г."

