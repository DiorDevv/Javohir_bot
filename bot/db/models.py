"""Ma'lumotlar bazasi jadvallari."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    Text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from bot.db.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    """Baholanadigan xodimlar (admin /employees orqali boshqaradi)."""

    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())

    feedbacks: Mapped[list[Feedback]] = relationship(back_populates="employee")

    def __repr__(self) -> str:
        return f"Employee(id={self.id}, full_name={self.full_name!r}, is_active={self.is_active})"


class Feedback(Base):
    """Bitta to'liq baholash javobi."""

    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint("timing_score BETWEEN 1 AND 5", name="ck_feedback_timing_score"),
        CheckConstraint("quality_score BETWEEN 1 AND 5", name="ck_feedback_quality_score"),
        # Spam tekshiruvi: (telegram_id, employee_id, created_at) bo'yicha qidiruv
        Index("ix_feedback_user_employee_created", "telegram_id", "employee_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(255))
    workplace: Mapped[str] = mapped_column(String(255))
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), index=True
    )
    function: Mapped[str] = mapped_column(String(255))
    timing_score: Mapped[int] = mapped_column(SmallInteger)
    timing_reason: Mapped[str] = mapped_column(Text)
    quality_score: Mapped[int] = mapped_column(SmallInteger)
    quality_reason: Mapped[str] = mapped_column(Text)
    suggestions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    employee: Mapped[Employee] = relationship(back_populates="feedbacks")
