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
        "|",
        "#",
        "[",
        "]",
        "‚",
        "!",
    )
    if any(marker in normalized for marker in garbage_markers):
        return True
    if re.search(r"[A-Za-z]{3,}", address) and not re.search(r"(?i)\b(?:street|avenue|road|prospekt|ramen|mario)\b", address):
        return True
    has_city = bool(re.search(r"(?i)\b(?:г\.?\s*москва|москва|санкт-петербург)\b", address))
    has_street = bool(re.search(r"(?i)\b(?:ул\.?|улица|наб\.?|набережная|пр-кт|проспект|переулок)\b", address))
    return not (has_city and has_street)


def lookup_address_online(restaurant_name: str | None, ocr_address: str | None, timeout: int = 8) -> AddressLookupResult | None:
    known_address = _known_restaurant_address(restaurant_name)
    if known_address:
        return AddressLookupResult(address=known_address, name=restaurant_name, source="проверенная база адресов")
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
    queries: list[str] = []
    if name and hint:
        queries.append(f"{name} {hint}")
    if name:
        queries.append(f"{name} Москва адрес")
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
    parts = [f"г. {city}" if city == "Москва" else city, road]
    if house:
        parts.append(f"д. {house}")
    if postcode:
        parts.append(postcode)
    return ", ".join(parts)


def _format_from_display_name(display_name: str) -> str | None:
    if not display_name:
        return None
    parts = [part.strip() for part in display_name.split(",") if part.strip()]
    city = next((part for part in parts if part == "Москва"), "")
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
    if not value:
        return None
    normalized = value.lower().replace("ё", "е")
    normalized = re.sub(r"(?i)\b(?:ресторан|кафе|бар|гриль|коптильня)\b", "", normalized)
    normalized = re.sub(r"[^a-zа-я0-9]+", "", normalized)
    if normalized in KNOWN_RESTAURANT_ADDRESSES:
        return KNOWN_RESTAURANT_ADDRESSES[normalized]
    for key, address in KNOWN_RESTAURANT_ADDRESSES.items():
        if key and key in normalized:
            return address
    return None


def _address_query_hint(value: str) -> str:
    lower = value.lower()
    if "вернад" in lower or "везна" in lower:
        return "Москва проспект Вернадского"
    if "преснен" in lower or "пpеснен" in lower:
        return "Москва Пресненская набережная 10"
    if "вавил" in lower:
        return "Москва улица Вавилова 1"
    city = "Москва" if re.search(r"(?i)(?:москва|hock|hoc)", value) else ""
    street_match = re.search(r"(?i)(?:ул\.?|улица|наб\.?|набережная|пр-кт|проспект)\s+[\wА-Яа-яЁё-]+", value)
    street = street_match.group(0) if street_match else ""
    return " ".join(part for part in (city, street) if part)


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
