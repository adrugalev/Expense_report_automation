from __future__ import annotations

APP_VERSION_DATE = "01.07.2026"
APP_VERSION_REVISION = 33


def app_version_label() -> str:
    return f"Версия {APP_VERSION_REVISION} от {APP_VERSION_DATE}"
