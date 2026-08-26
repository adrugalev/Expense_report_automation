from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.approval import apply_employee_business_rules
from src.models import Employee
from src.utils import slugify_file_part

from ..database_models import EmployeeRecord
from ..schemas.employee import EmployeeCreate, EmployeeResponse, EmployeeUpdate


class EmployeeNotFoundError(LookupError):
    pass


class EmployeeConflictError(ValueError):
    pass


class EmployeeService:
    def __init__(self, session: Session):
        self.session = session

    def list(self) -> list[EmployeeResponse]:
        records = self.session.scalars(select(EmployeeRecord).order_by(EmployeeRecord.full_name)).all()
        return [self._response(record) for record in records]

    def get_record(self, employee_id: str) -> EmployeeRecord:
        record = self.session.get(EmployeeRecord, employee_id)
        if not record:
            raise EmployeeNotFoundError(employee_id)
        return record

    def get_core(self, employee_id: str) -> Employee:
        return Employee.model_validate(self._response(self.get_record(employee_id)).model_dump())

    def create(self, data: EmployeeCreate) -> EmployeeResponse:
        employee_id = data.id or slugify_file_part(data.full_name.lower(), "employee")
        if self.session.get(EmployeeRecord, employee_id):
            raise EmployeeConflictError(f"Сотрудник с id '{employee_id}' уже существует")
        normalized = apply_employee_business_rules(Employee(id=employee_id, **data.model_dump(exclude={"id"})))
        record = EmployeeRecord(**normalized.model_dump())
        self.session.add(record)
        self.session.commit()
        return self._response(record)

    def update(self, employee_id: str, data: EmployeeUpdate) -> EmployeeResponse:
        record = self.get_record(employee_id)
        normalized = apply_employee_business_rules(Employee(id=employee_id, **data.model_dump()))
        for key, value in normalized.model_dump(exclude={"id"}).items():
            setattr(record, key, value)
        self.session.commit()
        return self._response(record)

    def delete(self, employee_id: str) -> None:
        record = self.get_record(employee_id)
        self.session.delete(record)
        self.session.commit()

    @staticmethod
    def _response(record: EmployeeRecord) -> EmployeeResponse:
        return EmployeeResponse.model_validate(
            {column.name: getattr(record, column.name) for column in EmployeeRecord.__table__.columns}
        )
