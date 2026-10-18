from __future__ import annotations

import re


_ADDRESS_LOWERCASE_WORDS = frozenset(
    "г город область обл край республика респ район р муниципальный муниципальная "
    "муниципальное округ городской поселение поселок посёлок пос деревня дер село с "
    "вн внутригородская внутригородское тер территория федерального значения автономный "
    "ул улица проспект пр проезд кт пер переулок наб набережная пл площадь "
    "б бульвар ш шоссе аллея тупик тракт мкр микрорайон квартал кв км "
    "д дом к корп корпус стр строение вл владение лит литера помещение пом "
    "оф офис этаж эт им имени лет летия года и на по при за".split()
)
_ADDRESS_ABBREVIATIONS = {word.casefold(): word for word in (
    "РФ", "СССР", "СНТ", "ДНТ", "ДНП", "ТСН", "ИЖС", "ЖК", "ТЦ", "ТРЦ", "БЦ",
    "ЦАО", "САО", "СВАО", "ВАО", "ЮВАО", "ЮАО", "ЮЗАО", "ЗАО", "СЗАО", "ЗелАО",
    "ХМАО", "ЯНАО", "ВДНХ", "СПб",
)}
_ADDRESS_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)


def normalize_address_case(value: str | None) -> str | None:
    if not value:
        return value

    def normalize_word(match: re.Match[str]) -> str:
        word = match.group()
        if not re.fullmatch(r"[А-Яа-яЁё]+", word):
            return word
        lower = word.lower()
        if re.search(r"\d-$", value[:match.start()]) and lower in {"я", "й", "е", "ая", "ое", "ый", "ой", "го"}:
            return lower
        # Keep house suffixes and identifiers unchanged, including 9А and к1.
        if (match.start() and value[match.start() - 1].isdigit()) or (match.end() < len(value) and value[match.end()].isdigit()):
            return word
        if lower in _ADDRESS_LOWERCASE_WORDS:
            return lower
        if lower in _ADDRESS_ABBREVIATIONS:
            return _ADDRESS_ABBREVIATIONS[lower]
        if word.isupper() and len(word) <= 2:
            return word
        return word.capitalize() if not word.islower() else word

    return _ADDRESS_WORD.sub(normalize_word, value)


def capitalize_first(value: str | None) -> str | None:
    if not value:
        return value
    stripped = value.strip()
    if not stripped:
        return stripped
    return stripped[0].upper() + stripped[1:]
