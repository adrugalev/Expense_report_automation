from datetime import date

from src.version import APP_VERSION_DATE, APP_VERSION_REVISION, app_version_label


def test_app_version_label_includes_revision_and_date() -> None:
    assert app_version_label() == f"Версия {APP_VERSION_REVISION} от {APP_VERSION_DATE}"


def test_app_version_date_matches_current_day() -> None:
    assert APP_VERSION_DATE == date.today().strftime("%d.%m.%Y")
