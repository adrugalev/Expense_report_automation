from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.employee_directory import EmployeeDirectory

from .config import Settings
from .database_models import EmployeeRecord, UserRecord
from .security import hash_password


logger = logging.getLogger(__name__)


def seed_initial_data(session: Session, settings: Settings) -> None:
    """Seed the admin, employee directory and one initial employee account."""

    employees_count = session.scalar(select(func.count()).select_from(EmployeeRecord)) or 0
    if employees_count == 0:
        directory = EmployeeDirectory(settings.legacy_data_dir)
        for employee in directory.sorted_employees():
            session.add(EmployeeRecord(**employee.model_dump()))
        logger.info("Seeded %s employees from the legacy directory", len(directory.employees))

    session.flush()
    admin_email = settings.admin_email.strip().lower()
    admin_employee_id = settings.admin_employee_id.strip()
    admin_employee = session.get(EmployeeRecord, admin_employee_id) if admin_employee_id else None
    existing_admin = session.scalar(
        select(UserRecord).where(UserRecord.role == "admin").order_by(UserRecord.created_at)
    )
    email_owner = session.scalar(select(UserRecord).where(UserRecord.email == admin_email))
    if existing_admin and email_owner and existing_admin.id != email_owner.id:
        raise RuntimeError("Admin email is already used by another account")
    admin_user = existing_admin or email_owner
    if not admin_user:
        admin_user = UserRecord(
            id=str(uuid4()),
            email=admin_email,
            full_name=settings.admin_name,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
        session.add(admin_user)
        logger.info("Created initial admin account for %s", admin_email)
    admin_user.email = admin_email
    admin_user.full_name = settings.admin_name
    admin_user.role = "admin"
    admin_user.employee_id = admin_employee.id if admin_employee else None

    for legacy_user in session.scalars(
        select(UserRecord).where(UserRecord.role.not_in(("admin", "employee")))
    ).all():
        legacy_user.role = "employee"

    employee_id = settings.employee_id.strip()
    employee = session.get(EmployeeRecord, employee_id) if employee_id else None
    if employee and employee.email:
        employee_email = employee.email.strip().lower()
        employee_user = session.scalar(select(UserRecord).where(UserRecord.employee_id == employee.id))
        email_owner = session.scalar(select(UserRecord).where(UserRecord.email == employee_email))
        if not employee_user and not email_owner:
            session.add(
                UserRecord(
                    id=str(uuid4()),
                    email=employee_email,
                    full_name=employee.full_name,
                    password_hash=hash_password(settings.employee_password),
                    role="employee",
                    employee_id=employee.id,
                )
            )
            logger.info("Created initial employee account for %s", employee_email)
        elif employee_user and employee_user.role != "admin":
            employee_user.full_name = employee.full_name
            employee_user.role = "employee"
        elif email_owner and email_owner.role != "admin":
            email_owner.employee_id = employee.id
            email_owner.full_name = employee.full_name
            email_owner.role = "employee"
    session.commit()
