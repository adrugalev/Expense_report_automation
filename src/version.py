from __future__ import annotations

APP_VERSION_DATE = "13.07.2026"
APP_VERSION_REVISION = 1


def app_version_label() -> str:
    return f"Версия {APP_VERSION_REVISION} от {APP_VERSION_DATE}"
