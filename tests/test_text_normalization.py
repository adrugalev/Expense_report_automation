from src.text_normalization import capitalize_first


def test_capitalize_first():
    assert capitalize_first("менеджер по продажам") == "Менеджер по продажам"
    assert capitalize_first("Руководитель направления продаж") == "Руководитель направления продаж"
    assert capitalize_first("") == ""
