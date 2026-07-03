from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "expense-report-automation/1.0"
KNOWN_RESTAURANT_ADDRESSES = {
    "коре": "г. Москва, ул. Вавилова, д. 1",
    "корё": "г. Москва, ул. Вавилова, д. 1",
    "smokebbq": "г. Москва, ул. Трубная, д. 18",
    "smokebbqбаргрилькоптильня": "г. Москва, ул. Трубная, д. 18",
    "корчма": "г. Москва, ул. Садовая-Кудринская, д. 3А",
    "одессамама": "г. Москва, Украинский б-р, д. 7",
    "юаньян": "г. Москва, ул. Сущевская, д. 27 стр. 2",
    "маньян": "г. Москва, ул. Сущевская, д. 27 стр. 2",
    "лонсин": "г. Москва, ул. Сущевская, д. 27 стр. 2",
    "50костей": "г. Екатеринбург, ул. 8 Марта, д. 23В",
    "mrhotрамен": "г. Москва, наб. Пресненская, д. 10",
    "mrhotramen": "г. Москва, наб. Пресненская, д. 10",
    "hrhotраней": "г. Москва, наб. Пресненская, д. 10",
    "osteriamario": "г. Москва, пр-кт Вернадского, д. 41",
    "osteriamarioшвили": "г. Москва, пр-кт Вернадского, д. 41",
    "швили": "г. Москва, пр-кт Вернадского, д. 41",
    "швипи": "г. Москва, пр-кт Вернадского, д. 41",
    "академгородок": "г. Москва, пр-кт Вернадского, д. 41",
    "вьетнамскаякухня": "г. Москва, наб. Пресненская, д. 12",
    "барruletaproom": "г. Москва, Староваганьковский пер., д. 19, стр. 7",
    "ruletaproom": "г. Москва, Староваганьковский пер., д. 19, стр. 7",
    "ruleфаргоом": "г. Москва, Староваганьковский пер., д. 19, стр. 7",
    "ruleсангоом": "г. Москва, Староваганьковский пер., д. 19, стр. 7",
    "барчик": "г. Москва, Староваганьковский пер., д. 19, стр. 7",
    "vasilchuki": "г. Москва, Флотская ул., д. 3",
    "ресторанvasilchuki": "г. Москва, Флотская ул., д. 3",
    "васильчуки": "г. Москва, Флотская ул., д. 3",
    "зверобой": "г. Екатеринбург, ул. Посадская, д. 28А",
    "звевобой": "г. Екатеринбург, ул. Посадская, д. 28А",
    "ресторанзверобой": "г. Екатеринбург, ул. Посадская, д. 28А",
    "frankbybasta": "г. Москва, ул. Сретенка, д. 24/2 стр. 1",
    "franktybasty": "г. Москва, ул. Сретенка, д. 24/2 стр. 1",
    "франкбайбаста": "г. Москва, ул. Сретенка, д. 24/2 стр. 1",
    "frank": "г. Москва, ул. Сретенка, д. 24/2 стр. 1",
    "клешниихвосты": "г. Москва, ул. Братиславская, д. 12",
    "кнешиихвосты": "г. Москва, ул. Братиславская, д. 12",
    "киешниихвосты": "г. Москва, ул. Братиславская, д. 12",
    "kleshnihvosti": "г. Москва, ул. Братиславская, д. 12",
    "rakovarnyakleshnihvosti": "г. Москва, ул. Братиславская, д. 12",
    "азбукавкуса": "г. Москва, ул. Люблинская, д. 96",
    "азвукаbkyc": "г. Москва, ул. Люблинская, д. 96",
    "азбукаbkус": "г. Москва, ул. Люблинская, д. 96",
    "ароматныймир": "г. Москва, ул. Люблинская, д. 76, к. 5",
    "ароматный": "г. Москва, ул. Люблинская, д. 76, к. 5",
    "алтайпремиум": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "алтайпремичм": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "алтайпремичи": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "алтайпремичн": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "алтайпремизи": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "altaipremium": "г. Москва, ул. Намёткина, д. 14, к. 1",
    "7727344960": "г. Москва, ул. Намёткина, д. 14, к. 1",
}
KNOWN_RESTAURANT_NAMES = {
    "коре": 'Ресторан "КОРЁ"',
    "корё": 'Ресторан "КОРЁ"',
    "smokebbq": "Smoke BBQ",
    "smokebbqбаргрилькоптильня": "Smoke BBQ",
    "корчма": "Корчма",
    "одессамама": "Одесса-мама",
    "юаньян": "Юаньян",
    "маньян": "Юаньян",
    "лонсин": "Юаньян",
    "50костей": "50 костей",
    "mrhotрамен": "Mr Hot Рамен",
    "mrhotramen": "Mr Hot Рамен",
    "hrhotраней": "Mr Hot Рамен",
    "osteriamario": "Osteria Mario & Швили",
    "osteriamarioшвили": "Osteria Mario & Швили",
    "швили": "Osteria Mario & Швили",
    "швипи": "Osteria Mario & Швили",
    "академгородок": "Osteria Mario & Швили",
    "вьетнамскаякухня": "Вьетнамская кухня",
    "барruletaproom": "Бар RULE taproom",
    "ruletaproom": "Бар RULE taproom",
    "ruleфаргоом": "Бар RULE taproom",
    "ruleсангоом": "Бар RULE taproom",
    "барчик": "Бар RULE taproom",
    "vasilchuki": "Ресторан Vasilchuki",
    "ресторанvasilchuki": "Ресторан Vasilchuki",
    "васильчуки": "Ресторан Vasilchuki",
    "зверобой": "Ресторан «Зверобой»",
    "звевобой": "Ресторан «Зверобой»",
    "ресторанзверобой": "Ресторан «Зверобой»",
    "frankbybasta": "Frank by Баста",
    "franktybasty": "Frank by Баста",
    "франкбайбаста": "Frank by Баста",
    "frank": "Frank by Баста",
    "клешниихвосты": "Раковарня «Клешни и Хвосты»",
    "кнешиихвосты": "Раковарня «Клешни и Хвосты»",
    "киешниихвосты": "Раковарня «Клешни и Хвосты»",
    "kleshnihvosti": "Раковарня «Клешни и Хвосты»",
    "rakovarnyakleshnihvosti": "Раковарня «Клешни и Хвосты»",
    "азбукавкуса": "Азбука вкуса",
    "азвукаbkyc": "Азбука вкуса",
    "азбукаbkус": "Азбука вкуса",
    "ароматныймир": "Ароматный мир",
    "ароматный": "Ароматный мир",
    "алтайпремиум": "Алтай Премиум",
    "алтайпремичм": "Алтай Премиум",
    "алтайпремичи": "Алтай Премиум",
    "алтайпремичн": "Алтай Премиум",
    "алтайпремизи": "Алтай Премиум",
    "altaipremium": "Алтай Премиум",
    "7727344960": "Алтай Премиум",
}


@dataclass(frozen=True)
class AddressLookupResult:
    address: str
    name: str | None = None
    source: str = "OpenStreetMap"


def should_lookup_address(address: str | None) -> bool:
    if not address:
        return True
    normalized = address.lower()
    if len(address.strip()) < 25:
        return True
    garbage_markers = (
        '"“*"-"ёъ',
        "скруг",
        "hock",
        "hoc",
        "мн el",
        "ilk",
        "…",
        "%с",
        "безналич",
        "итог",
        "сумма",
        "|",
        "#",
        "[",
        "]",
        "‚",
        "!",
        "косква",
        "екатев",
        "буюг",
        "сто.",
        "чек ы",
        "косл овый",
        "нолоин",
        "нальйно",
        "мальйо",
    )
    if any(marker in normalized for marker in garbage_markers):
        return True
    if re.search(r"[A-Za-z]{3,}", address) and not re.search(r"(?i)\b(?:street|avenue|road|prospekt|ramen|mario)\b", address):
        return True
    has_city = bool(re.search(r"(?i)\b(?:г\.?\s*москва|москва|г\.?\s*екатеринбург|екатеринбург|санкт-петербург)\b", address))
    has_street = bool(re.search(r"(?i)\b(?:ул\.?|улица|наб\.?|набережная|пр-кт|проспект|переулок)\b", address))
    return not (has_city and has_street)


def should_verify_restaurant_fields(restaurant_name: str | None, address: str | None) -> bool:
    if should_lookup_address(address):
        return True
    if _looks_suspicious_restaurant_name(restaurant_name):
        return True
    if _known_restaurant_address(restaurant_name) and address:
        known_address = _known_restaurant_address(restaurant_name) or ""
        return _street_key(known_address) != _street_key(address) or _house_key(known_address) != _house_key(address)
    return False


def lookup_address_online(restaurant_name: str | None, ocr_address: str | None, timeout: int = 8) -> AddressLookupResult | None:
    known_address = _known_restaurant_address(restaurant_name)
    if known_address:
        return AddressLookupResult(
            address=known_address,
            name=_known_restaurant_name(restaurant_name) or restaurant_name,
            source="проверенная база адресов",
        )
    queries = _build_queries(restaurant_name, ocr_address)
    for query in queries:
        result = _lookup_nominatim(query, timeout=timeout)
        if result:
            return result
    return None


def merge_online_address(online_address: str, ocr_address: str | None) -> str | None:
    ocr_house = _extract_house_number(ocr_address or "")
    online_house = _extract_house_number(online_address)
    if ocr_house and online_house and ocr_house != online_house:
        return None
    if ocr_house and not online_house:
        return _insert_house_number(online_address, ocr_house)
    return online_address


def _build_queries(restaurant_name: str | None, ocr_address: str | None) -> list[str]:
    name = _clean_restaurant_query(restaurant_name or "")
    hint = _address_query_hint(ocr_address or "")
    city = _city_query_hint(ocr_address or "")
    queries: list[str] = []
    if name and hint:
        queries.append(f"{name} {hint}")
    if name:
        queries.append(f"{name} {city or 'Москва'} адрес")
    if hint:
        queries.append(hint)
    unique: list[str] = []
    for query in queries:
        query = re.sub(r"\s+", " ", query).strip()
        if query and query not in unique:
            unique.append(query)
    return unique


def _lookup_nominatim(query: str, timeout: int) -> AddressLookupResult | None:
    params = urlencode(
        {
            "q": query,
            "format": "jsonv2",
            "limit": 3,
            "addressdetails": 1,
            "countrycodes": "ru",
        }
    )
    request = Request(f"{NOMINATIM_URL}?{params}", headers={"User-Agent": USER_AGENT})
    try:
        payload = urlopen(request, timeout=timeout).read().decode("utf-8")
        items = json.loads(payload)
    except Exception:
        return None
    for item in items:
        address = item.get("address") or {}
        if address.get("country_code") and address.get("country_code") != "ru":
            continue
        formatted = _format_nominatim_address(address, item.get("display_name") or "")
        if formatted and not should_lookup_address(formatted):
            return AddressLookupResult(address=formatted, name=item.get("name") or address.get("amenity"))
    return None


def _format_nominatim_address(address: dict, display_name: str) -> str | None:
    city = address.get("city") or address.get("town") or address.get("village") or address.get("state")
    road = address.get("road") or address.get("pedestrian") or address.get("footway")
    house = address.get("house_number")
    postcode = address.get("postcode")
    if not city or not road:
        return _format_from_display_name(display_name)
    parts = [f"г. {city}" if city in {"Москва", "Екатеринбург"} else city, road]
    if house:
        parts.append(f"д. {house}")
    if postcode:
        parts.append(postcode)
    return ", ".join(parts)


def _format_from_display_name(display_name: str) -> str | None:
    if not display_name:
        return None
    parts = [part.strip() for part in display_name.split(",") if part.strip()]
    city = next((part for part in parts if part in {"Москва", "Екатеринбург", "Санкт-Петербург"}), "")
    road = next((part for part in parts if re.search(r"(?i)(?:проспект|улица|набережная|пр-кт|наб\.)", part)), "")
    postcode = next((part for part in parts if re.fullmatch(r"\d{6}", part)), "")
    if not city or not road:
        return None
    result = [f"г. {city}", road]
    if postcode:
        result.append(postcode)
    return ", ".join(result)


def _clean_restaurant_query(value: str) -> str:
    value = re.sub(r"[^\wА-Яа-яЁё&\"«»\\s-]+", " ", value)
    value = value.replace("OSteria", "Osteria")
    value = value.replace("ШВИЛИ", "")
    value = re.sub(r"(?i)\b(?:ресторан|кафе)\b", "", value)
    return re.sub(r"\s+", " ", value).strip()


def _known_restaurant_address(value: str | None) -> str | None:
    return _known_restaurant_value(value, KNOWN_RESTAURANT_ADDRESSES)


def _known_restaurant_name(value: str | None) -> str | None:
    return _known_restaurant_value(value, KNOWN_RESTAURANT_NAMES)


def _known_restaurant_value(value: str | None, known_values: dict[str, str]) -> str | None:
    if not value:
        return None
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"(?i)\b(?:ресторан|кафе|бар|гриль|коптильня)\b", "", normalized)
    normalized = re.sub(r"[^a-zа-я0-9]+", "", normalized)
    if normalized in known_values:
        return known_values[normalized]
    for key, result in known_values.items():
        if key and key in normalized:
            return result
    return None


def _address_query_hint(value: str) -> str:
    lower = value.lower()
    if "вернад" in lower or "везна" in lower:
        return "Москва проспект Вернадского"
    if "преснен" in lower or "пpеснен" in lower:
        return "Москва Пресненская набережная 10"
    if "вавил" in lower:
        return "Москва улица Вавилова 1"
    if "вернад" in lower or "osteria" in lower or "швили" in lower or "швип" in lower or "академ" in lower:
        return "Москва проспект Вернадского 41"
    if "mr hot" in lower or "hr hot" in lower or "рамен" in lower or "раней" in lower:
        return "Москва Пресненская набережная 10"
    if "rule" in lower or "taproom" in lower or "барчик" in lower or "староваг" in lower:
        return "Москва Староваганьковский переулок 19"
    if "vasilchuki" in lower or "васильч" in lower or "флот" in lower:
        return "Москва Флотская улица 3"
    if "звер" in lower or "звев" in lower or "посад" in lower:
        return "Екатеринбург Посадская улица 28А"
    if "frank" in lower or "basta" in lower or "basty" in lower or "светен" in lower or "сретен" in lower:
        return "Москва улица Сретенка 24/2"
    if "клешн" in lower or "кнеш" in lower or "хвост" in lower or "хво" in lower or "братислав" in lower or "109451" in lower:
        return "Москва Братиславская улица 12"
    if "алтай" in lower or "altai" in lower or "наметк" in lower or "намётк" in lower or "7727344960" in lower:
        return "Москва улица Намёткина 14"
    city = _city_query_hint(value)
    street_match = re.search(r"(?i)(?:ул\.?|улица|наб\.?|набережная|пр-кт|проспект)\s+[\wА-Яа-яЁё-]+", value)
    street = street_match.group(0) if street_match else ""
    return " ".join(part for part in (city, street) if part)


def _city_query_hint(value: str) -> str:
    normalized = value.lower().replace("ё", "е")
    if re.search(r"(?i)(?:екатеринбург|екатев|буюг|свердловск)", normalized):
        return "Екатеринбург"
    if re.search(r"(?i)(?:москва|косква|hock|hoc)", normalized):
        return "Москва"
    if re.search(r"(?i)(?:санкт-петербург|петербург|спб)", normalized):
        return "Санкт-Петербург"
    return ""


def _looks_suspicious_restaurant_name(value: str | None) -> bool:
    if not value:
        return True
    normalized = value.lower().replace("ё", "е")
    if len(re.sub(r"[^a-zа-я0-9]+", "", normalized)) < 3:
        return True
    return bool(
        re.search(
            r"(?i)(?:расч[её]тов|пасчетов|зве[вй]об|нвстц|р[её]счетц|зн\s*ккт|рн\s*ккт|фн|фд|фп|рга\s*й)",
            normalized,
        )
    )


def _street_key(address: str) -> str:
    normalized = address.lower().replace("ё", "е")
    for key in (
        "посад",
        "сретен",
        "светен",
        "братислав",
        "наметк",
        "намётк",
        "флот",
        "преснен",
        "вернад",
        "вавил",
        "люблин",
        "трубн",
        "сущев",
        "украин",
        "староваг",
        "8 марта",
    ):
        if key in normalized:
            return key
    return ""


def _house_key(address: str) -> str:
    house = _extract_house_number(address)
    return house.lower().replace(" ", "") if house else ""


def _extract_house_number(value: str) -> str | None:
    match = re.search(r"(?i)\b(?:д|дом)[\.,]?\s*(\d+[А-Яа-яA-Za-z]?)\b", value)
    if match:
        return match.group(1)
    match = re.search(r"(?i)\b(?:ilk|lk|дк)\s*(\d+[А-Яа-яA-Za-z]?)\b", value)
    if match:
        return match.group(1)
    match = re.search(r"(?i)(?:ул\.?|улица|наб\.?|набережная|пр-кт|проспект)[^,\n]{0,80},\s*(\d+[А-Яа-яA-Za-z]?)\b", value)
    if not match:
        return None
    value = match.group(1)
    return None if re.fullmatch(r"\d{6}", value) else value


def _insert_house_number(address: str, house_number: str) -> str:
    parts = [part.strip() for part in address.split(",") if part.strip()]
    if len(parts) < 2:
        return f"{address}, д. {house_number}"
    if re.fullmatch(r"\d{6}", parts[-1]):
        parts.insert(-1, f"д. {house_number}")
    else:
        parts.append(f"д. {house_number}")
    return ", ".join(parts)
