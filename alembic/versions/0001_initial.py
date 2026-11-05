"""Boshlang'ich sxema: employees, feedback + standart xodimlar.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-05
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_EMPLOYEES = [
    "Kuchkarova Surayyo",
    "Arifxodjayeva Ziyoda",
    "Yodgorova Xolida",
]


def upgrade() -> None:
    employees = op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.UniqueConstraint("full_name", name="uq_employees_full_name"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("workplace", sa.String(length=255), nullable=False),
        sa.Column(
            "employee_id",
            sa.Integer(),
            sa.ForeignKey("employees.id", name="fk_feedback_employee_id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("function", sa.String(length=255), nullable=False),
        sa.Column("timing_score", sa.SmallInteger(), nullable=False),
        sa.Column("timing_reason", sa.Text(), nullable=False),
        sa.Column("quality_score", sa.SmallInteger(), nullable=False),
        sa.Column("quality_reason", sa.Text(), nullable=False),
        sa.Column("suggestions", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("timing_score BETWEEN 1 AND 5", name="ck_feedback_timing_score"),
        sa.CheckConstraint("quality_score BETWEEN 1 AND 5", name="ck_feedback_quality_score"),
    )
    op.create_index("ix_feedback_employee_id", "feedback", ["employee_id"])
    op.create_index(
        "ix_feedback_user_employee_created", "feedback", ["telegram_id", "employee_id", "created_at"]
    )

    op.bulk_insert(employees, [{"full_name": name, "is_active": True} for name in DEFAULT_EMPLOYEES])


def downgrade() -> None:
    op.drop_index("ix_feedback_user_employee_created", table_name="feedback")
    op.drop_index("ix_feedback_employee_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_table("employees")
