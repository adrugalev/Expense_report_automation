from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database_models import EmployeeRecord, UserRecord
from ..schemas.account import EmployeeAccountResponse
from ..security import hash_password


class AccountNotFoundError(LookupError):
    pass


class AccountConflictError(ValueError):
    pass


class AccountService:
    def __init__(self, session: Session):
        self.session = session

    def list_employee_accounts(self) -> list[EmployeeAccountResponse]:
        employees = self.session.scalars(select(EmployeeRecord).order_by(EmployeeRecord.full_name)).all()
        users = {
            user.employee_id: user
            for user in self.session.scalars(
                select(UserRecord).where(UserRecord.employee_id.is_not(None))
            ).all()
            if user.employee_id
        }
        return [self._response(employee, users.get(employee.id)) for employee in employees]

    def set_employee_password(self, employee_id: str, password: str) -> EmployeeAccountResponse:
        employee = self.session.get(EmployeeRecord, employee_id)
        if not employee:
            raise AccountNotFoundError(employee_id)
        if not employee.email:
            raise AccountConflictError("Сначала укажите email сотрудника в справочнике")

        normalized_email = employee.email.strip().lower()
        user = self.session.scalar(select(UserRecord).where(UserRecord.employee_id == employee_id))
        if user and user.role == "admin":
            raise AccountConflictError("Пароль администратора нельзя менять как пароль сотрудника")
        email_owner = self.session.scalar(select(UserRecord).where(UserRecord.email == normalized_email))
        if email_owner and email_owner.id != getattr(user, "id", None):
            raise AccountConflictError("Этот email уже используется другой учётной записью")

        if not user:
            user = UserRecord(
                id=str(uuid4()),
                email=normalized_email,
                full_name=employee.full_name,
                password_hash=hash_password(password),
                role="employee",
                employee_id=employee.id,
                is_active=True,
            )
            self.session.add(user)
        else:
            user.email = normalized_email
            user.full_name = employee.full_name
            user.password_hash = hash_password(password)
            user.role = "employee"
            user.is_active = True
        self.session.commit()
        return self._response(employee, user)

    @staticmethod
    def _response(employee: EmployeeRecord, user: UserRecord | None) -> EmployeeAccountResponse:
        return EmployeeAccountResponse(
            employee_id=employee.id,
            full_name=employee.full_name,
            email=employee.email,
            has_account=user is not None,
            is_active=bool(user and user.is_active),
            role=user.role if user else None,
        )
