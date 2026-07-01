from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP

try:
    from num2words import num2words
except Exception:  # pragma: no cover - optional runtime dependency fallback
    num2words = None


MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


def format_rubles(amount: Decimal | int | float | str, with_kopecks: bool = True) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    whole, fraction = f"{value:.2f}".split(".")
    whole_grouped = f"{int(whole):,}".replace(",", " ")
    if with_kopecks:
        return f"{whole_grouped},{fraction} ₽"
    return f"{whole_grouped} ₽"


def format_date_ru(value: date | None) -> str:
    if value is None:
        return ""
    return f"{value.day} {MONTHS_RU[value.month]} {value.year} г."


def amount_to_words_ru(amount: Decimal | int | float | str) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    rubles = int(value)
    kopecks = int((value - rubles) * 100)
    if num2words is not None:
        words = num2words(rubles, lang="ru").replace("один", "один").strip()
    else:
        words = _small_number_to_words(rubles)
    ruble_word = _plural_ru(rubles, "рубль", "рубля", "рублей")
    return f"{words} {ruble_word} {kopecks:02d} копеек"


def _plural_ru(number: int, one: str, few: str, many: str) -> str:
    n = abs(number) % 100
    n1 = n % 10
    if 11 <= n <= 19:
        return many
    if n1 == 1:
        return one
    if 2 <= n1 <= 4:
        return few
    return many


def _small_number_to_words(number: int) -> str:
    # Compact fallback for test/dev environments without num2words.
    units = [
        "ноль",
        "один",
        "два",
        "три",
        "четыре",
        "пять",
        "шесть",
        "семь",
        "восемь",
        "девять",
        "десять",
        "одиннадцать",
        "двенадцать",
        "тринадцать",
        "четырнадцать",
        "пятнадцать",
        "шестнадцать",
        "семнадцать",
        "восемнадцать",
        "девятнадцать",
    ]
    tens = {
        20: "двадцать",
        30: "тридцать",
        40: "сорок",
        50: "пятьдесят",
        60: "шестьдесят",
        70: "семьдесят",
        80: "восемьдесят",
        90: "девяносто",
    }
    if number < 20:
        return units[number]
    if number < 100:
        return tens[number // 10 * 10] + ("" if number % 10 == 0 else f" {units[number % 10]}")
    return str(number)

