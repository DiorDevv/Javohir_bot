"""DB bilan ishlash funksiyalari (handlerlar to'g'ridan-to'g'ri SQL yozmaydi)."""
from __future__ import annotations

import enum
from collections import Counter
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db.models import Employee, Feedback, utcnow

# --- Xodimlar ---------------------------------------------------------------


async def list_employees(session: AsyncSession, *, active_only: bool = True) -> list[Employee]:
    stmt = select(Employee).order_by(Employee.full_name)
    if active_only:
        stmt = stmt.where(Employee.is_active.is_(True))
    return list((await session.scalars(stmt)).all())


async def get_employee(session: AsyncSession, employee_id: int) -> Employee | None:
    return await session.get(Employee, employee_id)


async def add_employee(session: AsyncSession, full_name: str) -> tuple[Employee, bool]:
    """Xodim qo'shadi. Natija: (xodim, yangi_yaratildimi).

    Agar shu nomli nofaol xodim bo'lsa — u qayta faollashtiriladi.
    """
    existing = await session.scalar(
        select(Employee).where(func.lower(Employee.full_name) == full_name.lower())
    )
    if existing is not None:
        if existing.is_active:
            return existing, False
        existing.is_active = True
        await session.commit()
        return existing, True

    employee = Employee(full_name=full_name, is_active=True)
    session.add(employee)
    await session.commit()
    return employee, True


async def toggle_employee(session: AsyncSession, employee_id: int) -> Employee | None:
    employee = await session.get(Employee, employee_id)
    if employee is None:
        return None
    employee.is_active = not employee.is_active
    await session.commit()
    return employee


class DeleteResult(enum.Enum):
    DELETED = "deleted"
    DEACTIVATED = "deactivated"  # baholari bor — faqat nofaol qilindi
    NOT_FOUND = "not_found"


async def delete_employee(session: AsyncSession, employee_id: int) -> tuple[DeleteResult, str]:
    employee = await session.get(Employee, employee_id)
    if employee is None:
        return DeleteResult.NOT_FOUND, ""
    name = employee.full_name
    feedback_count = await session.scalar(
        select(func.count(Feedback.id)).where(Feedback.employee_id == employee_id)
    )
    if feedback_count:
        employee.is_active = False
        await session.commit()
        return DeleteResult.DEACTIVATED, name
    await session.delete(employee)
    await session.commit()
    return DeleteResult.DELETED, name


# --- Baholashlar ------------------------------------------------------------


async def has_recent_feedback(
    session: AsyncSession, telegram_id: int, employee_id: int, hours: int
) -> bool:
    """Foydalanuvchi oxirgi `hours` soat ichida shu xodimni baholaganmi."""
    if hours <= 0:
        return False
    since = utcnow() - timedelta(hours=hours)
    found = await session.scalar(
        select(Feedback.id)
        .where(
            Feedback.telegram_id == telegram_id,
            Feedback.employee_id == employee_id,
            Feedback.created_at >= since,
        )
        .limit(1)
    )
    return found is not None


async def create_feedback(session: AsyncSession, **values: Any) -> Feedback:
    feedback = Feedback(**values)
    session.add(feedback)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    return feedback


async def list_feedback_with_employee(session: AsyncSession) -> list[tuple[Feedback, str]]:
    stmt = (
        select(Feedback, Employee.full_name)
        .join(Employee, Feedback.employee_id == Employee.id)
        .order_by(Feedback.created_at, Feedback.id)
    )
    return [(row[0], row[1]) for row in (await session.execute(stmt)).all()]


# --- Statistika ---------------------------------------------------------------


@dataclass(slots=True)
class EmployeeStats:
    full_name: str
    is_active: bool
    count: int
    avg_timing: float | None
    avg_quality: float | None


@dataclass(slots=True)
class Stats:
    total: int
    unique_users: int
    avg_timing: float | None
    avg_quality: float | None
    employees: list[EmployeeStats] = field(default_factory=list)
    by_workplace: list[tuple[str, int]] = field(default_factory=list)
    by_function: list[tuple[str, int]] = field(default_factory=list)


def _to_float(value: Any) -> float | None:
    return None if value is None else float(value)


async def get_stats(session: AsyncSession) -> Stats:
    total, unique_users, avg_timing, avg_quality = (
        await session.execute(
            select(
                func.count(Feedback.id),
                func.count(distinct(Feedback.telegram_id)),
                func.avg(Feedback.timing_score),
                func.avg(Feedback.quality_score),
            )
        )
    ).one()

    per_employee = (
        await session.execute(
            select(
                Employee.full_name,
                Employee.is_active,
                func.count(Feedback.id),
                func.avg(Feedback.timing_score),
                func.avg(Feedback.quality_score),
            )
            .outerjoin(Feedback, Feedback.employee_id == Employee.id)
            .group_by(Employee.id, Employee.full_name, Employee.is_active)
            .order_by(Employee.full_name)
        )
    ).all()

    by_workplace = (
        await session.execute(
            select(Feedback.workplace, func.count(Feedback.id))
            .group_by(Feedback.workplace)
            .order_by(func.count(Feedback.id).desc())
        )
    ).all()

    # "Boshqa: ..." javoblari bitta "Va boshqa" guruhiga birlashtiriladi
    function_counter: Counter[str] = Counter()
    for name, count in (
        await session.execute(select(Feedback.function, func.count(Feedback.id)).group_by(Feedback.function))
    ).all():
        key = texts.FUNCTIONS[texts.FUNCTION_OTHER] if name.startswith(texts.FUNCTION_OTHER_PREFIX) else name
        function_counter[key] += count

    return Stats(
        total=int(total or 0),
        unique_users=int(unique_users or 0),
        avg_timing=_to_float(avg_timing),
        avg_quality=_to_float(avg_quality),
        employees=[
            EmployeeStats(
                full_name=name,
                is_active=bool(active),
                count=int(count),
                avg_timing=_to_float(t),
                avg_quality=_to_float(q),
            )
            for name, active, count, t, q in per_employee
        ],
        by_workplace=[(name, int(count)) for name, count in by_workplace],
        by_function=function_counter.most_common(),
    )
