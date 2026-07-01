from __future__ import annotations


def capitalize_first(value: str | None) -> str | None:
    if not value:
        return value
    stripped = value.strip()
    if not stripped:
        return stripped
    return stripped[0].upper() + stripped[1:]
