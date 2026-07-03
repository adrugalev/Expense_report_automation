import json
from urllib.parse import parse_qs, urlsplit

from src.address_lookup import lookup_address_online, merge_online_address, should_lookup_address, should_verify_restaurant_fields


def test_should_lookup_ocr_garbage_address():
    assert should_lookup_address('Г. Москва, Вн. Тер.Г. "“*"-"ЁЪ} ВЛЬНЫЙ СКРУГ ПРОСлект Вернадско')
    assert not should_lookup_address("г. Москва, проспект Вернадского, 119415")


def test_lookup_address_online_uses_nominatim(monkeypatch):
    payload = [
        {
            "name": "Остерия Марио",
            "display_name": "Остерия Марио, проспект Вернадского, Москва, 119415, Россия",
            "address": {
                "amenity": "Остерия Марио",
                "road": "проспект Вернадского",
                "city": "Москва",
                "postcode": "119415",
                "country_code": "ru",
            },
        }
    ]

    class Response:
        def read(self):
            return json.dumps(payload).encode("utf-8")

    monkeypatch.setattr("src.address_lookup.urlopen", lambda request, timeout: Response())

    result = lookup_address_online("Новый ресторан", 'Г. Москва, Вн. Тер.Г. "“*"-"ЁЪ} ВЛЬНЫЙ СКРУГ ПРОСлект Вернадско')

    assert result
    assert result.address == "г. Москва, проспект Вернадского, 119415"
    assert result.name == "Остерия Марио"


def test_lookup_address_online_prefers_known_restaurant_address(monkeypatch):
    def fail_urlopen(request, timeout):
        raise AssertionError("Known restaurant address should not call online fallback")

    monkeypatch.setattr("src.address_lookup.urlopen", fail_urlopen)

    result = lookup_address_online(
        "Ресторан “КОРЕ”",
        "г. Москва, BH. TeP. Г, МУНИ ципальный ОКРУГ ДоНскОЙ, 115419, ул. Вавилова › д. 1",
    )

    assert result
    assert result.address == "г. Москва, ул. Вавилова, д. 1"


def test_lookup_address_online_returns_known_restaurant_name_and_address(monkeypatch):
    def fail_urlopen(request, timeout):
        raise AssertionError("Known restaurant address should not call online fallback")

    monkeypatch.setattr("src.address_lookup.urlopen", fail_urlopen)

    result = lookup_address_online("Ресторан “Звевобой“", "г. Екатевинбуюг. ул. Посадская. сто. 2 ВА")

    assert result
    assert result.name == "Ресторан «Зверобой»"
    assert result.address == "г. Екатеринбург, ул. Посадская, д. 28А"


def test_lookup_address_online_returns_known_gift_store_name_and_address(monkeypatch):
    def fail_urlopen(request, timeout):
        raise AssertionError("Known store address should not call online fallback")

    monkeypatch.setattr("src.address_lookup.urlopen", fail_urlopen)

    result = lookup_address_online("М&Е \"Ароматный", "109382, , МОСкба, _ Люблинская ул. , 0.76) K.5")

    assert result
    assert result.name == "Ароматный мир"
    assert result.address == "г. Москва, ул. Люблинская, д. 76, к. 5"


def test_should_verify_restaurant_fields_for_ocr_name_and_address():
    assert should_verify_restaurant_fields("Ресторан “Звевобой“", "г. Екатевинбуюг. ул. Посадская. сто. 2 ВА")
    assert not should_verify_restaurant_fields("Остерия Марио", "г. Москва, проспект Вернадского, 119415")


def test_lookup_address_online_uses_city_from_ocr_address(monkeypatch):
    captured_queries = []
    payload = [
        {
            "name": "Новый ресторан",
            "display_name": "Новый ресторан, Посадская улица, Екатеринбург, Россия",
            "address": {
                "amenity": "Новый ресторан",
                "road": "Посадская улица",
                "house_number": "28А",
                "city": "Екатеринбург",
                "country_code": "ru",
            },
        }
    ]

    class Response:
        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(request, timeout):
        query = parse_qs(urlsplit(request.full_url).query).get("q", [""])[0]
        captured_queries.append(query)
        return Response()

    monkeypatch.setattr("src.address_lookup.urlopen", fake_urlopen)

    result = lookup_address_online("Новый ресторан", "г. Екатевинбуюг. ул. Посадская. сто. 2 ВА")

    assert result
    assert result.address == "г. Екатеринбург, Посадская улица, д. 28А"
    assert captured_queries
    assert "Екатеринбург" in captured_queries[0]


def test_merge_online_address_preserves_ocr_house_number():
    assert (
        merge_online_address("г. Москва, Пресненская набережная, 123112", "г Москва, наб Пресненская, д. 10")
        == "г. Москва, Пресненская набережная, д. 10, 123112"
    )
    assert merge_online_address("г. Москва, улица Вавилова, д. 38 к1, 117312", "ул. Вавилова, д. 1") is None
