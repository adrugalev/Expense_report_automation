from src.phone import normalize_ru_phone


def test_normalize_ru_phone():
    assert normalize_ru_phone("+7 962 773-99-77") == "+7 (962) 773-99-77"
    assert normalize_ru_phone("+7(922) 933-89-98") == "+7 (922) 933-89-98"
    assert normalize_ru_phone("8 926 110 42 59") == "+7 (926) 110-42-59"
