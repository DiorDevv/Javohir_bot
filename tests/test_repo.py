from __future__ import annotations

from datetime import timedelta

from openpyxl import load_workbook
from io import BytesIO
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db import repo
from bot.db.models import utcnow
from bot.utils.export import build_feedback_xlsx


def _feedback(employee_id: int, telegram_id: int = 1, **overrides: object) -> dict[str, object]:
    values: dict[str, object] = dict(
        telegram_id=telegram_id,
        username="tester",
        full_name="Aliyev Vali",
        workplace="Bosh ofis",
        employee_id=employee_id,
        function="Ta'tillar",
        timing_score=4,
        timing_reason="Tez bajarildi",
        quality_score=5,
        quality_reason="Sifatli",
        suggestions=None,
    )
    values.update(overrides)
    return values


async def test_cooldown(session: AsyncSession) -> None:
    emp = (await repo.list_employees(session))[0]
    assert not await repo.has_recent_feedback(session, 1, emp.id, 24)
    await repo.create_feedback(session, **_feedback(emp.id))
    assert await repo.has_recent_feedback(session, 1, emp.id, 24)
    assert not await repo.has_recent_feedback(session, 1, emp.id, 0)  # 0 = cheklovsiz
    assert not await repo.has_recent_feedback(session, 2, emp.id, 24)  # boshqa foydalanuvchi


async def test_cooldown_expires(session: AsyncSession) -> None:
    emp = (await repo.list_employees(session))[0]
    await repo.create_feedback(
        session, **_feedback(emp.id, created_at=utcnow() - timedelta(hours=25))
    )
    assert not await repo.has_recent_feedback(session, 1, emp.id, 24)


async def test_stats_and_export(session: AsyncSession) -> None:
    emps = await repo.list_employees(session)
    await repo.create_feedback(session, **_feedback(emps[0].id, timing_score=2, quality_score=4))
    await repo.create_feedback(session, **_feedback(emps[0].id, telegram_id=2, timing_score=4))
    await repo.create_feedback(
        session, **_feedback(emps[1].id, telegram_id=2, function="Boshqa: Malaka oshirish")
    )

    stats = await repo.get_stats(session)
    assert stats.total == 3
    assert stats.unique_users == 2
    first = next(e for e in stats.employees if e.full_name == emps[0].full_name)
    assert first.count == 2 and first.avg_timing == 3.0 and first.avg_quality == 4.5
    assert dict(stats.by_function) == {"Ta'tillar": 2, "Va boshqa": 1}
    assert any(e.count == 0 for e in stats.employees)

    rows = await repo.list_feedback_with_employee(session)
    wb = load_workbook(BytesIO(build_feedback_xlsx(rows, "Asia/Tashkent")))
    ws = wb.active
    assert ws.max_row == 4
    assert ws.cell(row=2, column=7).value == emps[0].full_name


async def test_employee_management(session: AsyncSession) -> None:
    emp, created = await repo.add_employee(session, "Aliyeva Malika")
    assert created
    _, created_again = await repo.add_employee(session, "aliyeva malika")
    assert not created_again

    toggled = await repo.toggle_employee(session, emp.id)
    assert toggled is not None and not toggled.is_active
    assert emp.id not in {e.id for e in await repo.list_employees(session)}

    result, _ = await repo.delete_employee(session, emp.id)
    assert result is repo.DeleteResult.DELETED

    rated = (await repo.list_employees(session))[0]
    await repo.create_feedback(session, **_feedback(rated.id))
    result, _ = await repo.delete_employee(session, rated.id)
    assert result is repo.DeleteResult.DEACTIVATED
