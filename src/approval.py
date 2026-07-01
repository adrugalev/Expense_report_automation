from __future__ import annotations

from .models import Employee
from .phone import normalize_ru_phone
from .text_normalization import capitalize_first


DRUGALEV_EMPLOYEE_ID = "drugalev"
DRUGALEV_FULL_NAME = "Другалев Александр Александрович"
DRUGALEV_POSITION = "Руководитель направления продаж"


def is_drugalev(employee: Employee) -> bool:
    normalized_name = employee.full_name.lower().replace("ё", "е")
    return employee.id == DRUGALEV_EMPLOYEE_ID or "другалев" in normalized_name


def default_approver_for(employee: Employee) -> str:
    if is_drugalev(employee):
        return ""
    return DRUGALEV_FULL_NAME


def apply_employee_business_rules(employee: Employee) -> Employee:
    updates: dict[str, str] = {}
    if is_drugalev(employee):
        updates["position"] = DRUGALEV_POSITION
        updates["manager_name"] = ""
        updates["manager_position"] = ""
    elif not employee.manager_name:
        updates["manager_name"] = DRUGALEV_FULL_NAME
        updates["manager_position"] = DRUGALEV_POSITION
    normalized_phone = normalize_ru_phone(employee.phone)
    if normalized_phone != employee.phone:
        updates["phone"] = normalized_phone
    normalized_position = capitalize_first(updates.get("position", employee.position))
    if normalized_position != updates.get("position", employee.position):
        updates["position"] = normalized_position
    normalized_manager_position = capitalize_first(updates.get("manager_position", employee.manager_position))
    if normalized_manager_position != updates.get("manager_position", employee.manager_position):
        updates["manager_position"] = normalized_manager_position
    return employee.model_copy(update=updates) if updates else employee
