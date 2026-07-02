import json

from src.address_lookup import lookup_address_online, merge_online_address, should_lookup_address


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


def test_merge_online_address_preserves_ocr_house_number():
    assert (
        merge_online_address("г. Москва, Пресненская набережная, 123112", "г Москва, наб Пресненская, д. 10")
        == "г. Москва, Пресненская набережная, д. 10, 123112"
    )
    assert merge_online_address("г. Москва, улица Вавилова, д. 38 к1, 117312", "ул. Вавилова, д. 1") is None
