from src.approval import default_approver_for, is_drugalev
from src.models import Employee


def test_drugalev_has_no_approver():
    employee = Employee(
        id="drugalev",
        full_name="Другалев Александр Александрович",
        position="Руководитель направления продаж",
    )

    assert is_drugalev(employee)
    assert default_approver_for(employee) == ""


def test_other_employee_approver_is_drugalev():
    employee = Employee(full_name="Иванов Иван", position="Менеджер")

    assert not is_drugalev(employee)
    assert default_approver_for(employee) == "Другалев Александр Александрович"
