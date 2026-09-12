"""Link employee accounts to employee directory records.

Revision ID: 20260826_0002
Revises: 20260825_0001
Create Date: 2026-08-26
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260826_0002"
down_revision = "20260825_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("users")}
    if "employee_id" not in columns:
        with op.batch_alter_table("users") as batch:
            batch.add_column(sa.Column("employee_id", sa.String(length=100), nullable=True))
            batch.create_foreign_key(
                "fk_users_employee_id_employees",
                "employees",
                ["employee_id"],
                ["id"],
                ondelete="SET NULL",
            )

    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("users")}
    if "ix_users_employee_id" not in indexes:
        op.create_index("ix_users_employee_id", "users", ["employee_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_index("ix_users_employee_id")
        batch.drop_constraint("fk_users_employee_id_employees", type_="foreignkey")
        batch.drop_column("employee_id")
