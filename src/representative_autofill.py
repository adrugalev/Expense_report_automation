from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROFILES_PATH = PROJECT_ROOT / "data" / "representative_profiles.json"


def _load_profiles() -> list[dict[str, Any]]:
    return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))


REPRESENTATIVE_AUTOFILL_PROFILES = _load_profiles()


def profile_by_counterparty(counterparty: str) -> dict[str, Any]:
    """Return a representative-expense profile by its stable display name."""

    for profile in REPRESENTATIVE_AUTOFILL_PROFILES:
        if profile["counterparty"] == counterparty:
            return profile
    return REPRESENTATIVE_AUTOFILL_PROFILES[0]


def choose_profile(signature: str, recent_counterparties: Iterable[str] = ()) -> dict[str, Any]:
    """Choose a deterministic profile while avoiding the three most recent companies."""

    recent = list(recent_counterparties)
    candidates = [
        profile
        for profile in REPRESENTATIVE_AUTOFILL_PROFILES
        if profile["counterparty"] not in set(recent[-3:])
    ] or REPRESENTATIVE_AUTOFILL_PROFILES
    seed = sum(ord(char) for char in signature)
    return candidates[seed % len(candidates)]


def results_from_purposes(purpose_text: str) -> list[str]:
    """Build concise result statements from user-entered meeting purposes."""

    results: list[str] = []
    for line in _split_lines(purpose_text):
        normalized = line.strip().rstrip(".;")
        lowered = normalized.lower()
        if lowered.startswith("обсудить "):
            results.append(f"Обсужден{normalized[len('обсудить'):]}".strip())
        elif lowered.startswith("решить "):
            results.append(f"Решен{normalized[len('решить'):]}".strip())
        elif lowered.startswith("договориться "):
            results.append(f"Достигнута договоренность{normalized[len('договориться'):]}".strip())
        elif lowered.startswith("провести встречу"):
            details = normalized[len("провести встречу") :].strip()
            results.append(f"Достигнута договоренность о встрече{' ' + details if details else ''}".strip())
        elif lowered.startswith("согласовать "):
            results.append(f"Согласован{normalized[len('согласовать'):]}".strip())
        elif lowered.startswith("уточнить "):
            results.append(f"Уточнен{normalized[len('уточнить'):]}".strip())
        elif lowered.startswith("презентовать "):
            results.append(f"Проведена презентация{normalized[len('презентовать'):]}".strip())
        else:
            results.append(f"Достигнут результат по задаче: {normalized}")
    return results


def complete_representative_fields(data: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Fill optional representative-expense fields using a selected business profile."""

    completed = dict(data)
    user_purpose = str(completed.get("meeting_purpose") or "").strip()
    if not str(completed.get("counterparty") or "").strip():
        completed["counterparty"] = profile["counterparty"]
    if not user_purpose:
        completed["meeting_purpose"] = "\n".join(profile["purposes"])
    if not str(completed.get("meeting_result") or "").strip():
        completed["meeting_result"] = (
            "\n".join(results_from_purposes(user_purpose))
            if user_purpose
            else "\n".join(profile["results"])
        )
    if not completed.get("participants_counterparty"):
        completed["participants_counterparty"] = [
            f"{name}, {position}" for name, position in profile["participants"]
        ]
    return completed


def _split_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]
