from pathlib import Path

from src.employee_directory import EmployeeDirectory
from src.models import Employee


def test_employee_directory_add_update_and_get(tmp_path):
    directory = EmployeeDirectory(tmp_path)
    employee = directory.add(Employee(full_name="Иванов Иван", position="Менеджер"))

    assert directory.get_by_id(employee.id).full_name == "Иванов Иван"

    directory.update(employee.id, Employee(full_name="Иванов Иван", position="Директор"))
    assert directory.get_by_id(employee.id).position == "Директор"
    assert directory.options()
    assert directory.options() == ["Иванов Иван"]


def test_employee_directory_sets_drugalev_as_default_approver(tmp_path):
    directory = EmployeeDirectory(tmp_path)
    employee = directory.add(Employee(full_name="Иванов Иван", position="Менеджер"))

    saved = directory.get_by_id(employee.id)

    assert saved.manager_name == "Другалев Александр Александрович"
    assert saved.manager_position == "Руководитель направления продаж"


def test_employee_directory_keeps_drugalev_without_approver(tmp_path):
    directory = EmployeeDirectory(tmp_path)
    employee = directory.add(Employee(id="drugalev", full_name="Другалев Александр Александрович", position="Контактное лицо"))

    saved = directory.get_by_id(employee.id)

    assert saved.position == "Руководитель направления продаж"
    assert saved.manager_name == ""


def test_employee_directory_options_are_sorted_without_positions(tmp_path):
    directory = EmployeeDirectory(tmp_path)
    directory.add(Employee(full_name="Попов Леонид", position="Менеджер"))
    directory.add(Employee(full_name="Баранова Гиляна", position="Менеджер"))
    directory.add(Employee(full_name="Зимин Сергей", position="Менеджер"))

    assert directory.options() == ["Баранова Гиляна", "Зимин Сергей", "Попов Леонид"]


def test_seeded_zimin_position_is_project_manager() -> None:
    directory = EmployeeDirectory(Path(__file__).resolve().parents[1] / "data")

    zimin = directory.get_by_id("zimin")

    assert zimin is not None
    assert zimin.position == "Руководитель проекта"
