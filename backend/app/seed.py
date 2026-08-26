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
    """Seed the admin user and legacy employee directory on first startup."""

    admin_email = settings.admin_email.strip().lower()
    existing_admin = session.scalar(select(UserRecord).where(UserRecord.email == admin_email))
    if not existing_admin:
        session.add(
            UserRecord(
                id=str(uuid4()),
                email=admin_email,
                full_name=settings.admin_name,
                password_hash=hash_password(settings.admin_password),
                role="admin",
            )
        )
        logger.info("Created initial admin account for %s", admin_email)

    employees_count = session.scalar(select(func.count()).select_from(EmployeeRecord)) or 0
    if employees_count == 0:
        directory = EmployeeDirectory(settings.legacy_data_dir)
        for employee in directory.sorted_employees():
            session.add(EmployeeRecord(**employee.model_dump()))
        logger.info("Seeded %s employees from the legacy directory", len(directory.employees))
    session.commit()
