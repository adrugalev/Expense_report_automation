from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .models import Employee
from .approval import apply_employee_business_rules
from .phone import normalize_ru_phone
from .text_normalization import capitalize_first
from .utils import slugify_file_part


class EmployeeDirectory:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.json_path = data_dir / "employees.json"
        self.xlsx_path = data_dir / "employees.xlsx"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.employees: list[Employee] = []
        self.load()

    def load(self) -> list[Employee]:
        if self.json_path.exists():
            raw = json.loads(self.json_path.read_text(encoding="utf-8"))
            self.employees = [apply_employee_business_rules(Employee.model_validate(item)) for item in raw]
        elif self.xlsx_path.exists():
            rows = pd.read_excel(self.xlsx_path).fillna("").to_dict("records")
            self.employees = [apply_employee_business_rules(Employee.model_validate(row)) for row in rows]
        else:
            self.employees = []
            self.save()
        return self.employees

    def save(self) -> None:
        payload = [employee.model_dump(mode="json") for employee in self.employees]
        self.json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def options(self) -> list[str]:
        return [self.label_for(employee) for employee in self.sorted_employees()]

    def sorted_employees(self) -> list[Employee]:
        return sorted(self.employees, key=lambda employee: employee.full_name.casefold())

    @staticmethod
    def label_for(employee: Employee) -> str:
        return employee.full_name

    def get_by_id(self, employee_id: str) -> Employee | None:
        return next((employee for employee in self.employees if employee.id == employee_id), None)

    def get_by_label(self, label: str) -> Employee | None:
        labels = {self.label_for(employee): employee for employee in self.employees}
        return labels.get(label)

    def add(self, employee: Employee) -> Employee:
        employee_id = employee.id or slugify_file_part(employee.full_name.lower(), "employee")
        if self.get_by_id(employee_id):
            raise ValueError(f"Сотрудник с id '{employee_id}' уже существует")
        employee = apply_employee_business_rules(employee.model_copy(update={"id": employee_id}))
        self.employees.append(employee)
        self.save()
        return employee

    def update(self, employee_id: str, employee: Employee) -> Employee:
        for index, existing in enumerate(self.employees):
            if existing.id == employee_id:
                updated = apply_employee_business_rules(employee.model_copy(update={"id": employee_id}))
                self.employees[index] = updated
                self.save()
                return updated
        raise KeyError(f"Сотрудник с id '{employee_id}' не найден")


def employee_from_form_data(data: dict[str, str]) -> Employee:
    return Employee(
        id=data.get("id") or None,
        full_name=data["full_name"],
        short_name=data.get("short_name") or None,
        position=capitalize_first(data["position"]),
        department=data.get("department", ""),
        company=data.get("company") or None,
        phone=normalize_ru_phone(data.get("phone")) or None,
        email=data.get("email") or None,
        manager_name=data.get("manager_name") or None,
        manager_position=data.get("manager_position") or None,
        default_signatory_name=data.get("default_signatory_name") or None,
        default_signatory_position=data.get("default_signatory_position") or None,
    )
