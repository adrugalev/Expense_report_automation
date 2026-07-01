from __future__ import annotations

import re


def normalize_ru_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = re.sub(r"\D+", "", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}"
    return value.strip()
