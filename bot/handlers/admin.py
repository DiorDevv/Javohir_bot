"""Admin buyruqlari: /stats, /export, /employees."""
from __future__ import annotations

import html
import logging
from contextlib import suppress
from datetime import datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.config import Settings
from bot.db import repo
from bot.filters import IsAdmin
from bot.keyboards import admin as kb
from bot.keyboards.callbacks import AdminEmpCb
from bot.states import AdminStates
from bot.utils.export import build_feedback_xlsx
from bot.utils.text import fmt_score, split_message
from bot.utils.validators import validate_full_name

logger = logging.getLogger(__name__)

router = Router(name="admin")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# --- /stats -------------------------------------------------------------------


def format_stats(stats: repo.Stats) -> str:
    if stats.total == 0:
        return texts.STATS_EMPTY

    lines = [
        "📊 <b>Umumiy statistika</b>",
        "",
        f"📝 Jami baholashlar: <b>{stats.total}</b>",
        f"👥 Ishtirokchilar: <b>{stats.unique_users}</b>",
        f"⏱ O'rtacha ball (muddat): <b>{fmt_score(stats.avg_timing)}</b>",
        f"⭐️ O'rtacha ball (sifat): <b>{fmt_score(stats.avg_quality)}</b>",
        "",
        "👤 <b>Xodimlar bo'yicha</b>",
    ]
    for index, emp in enumerate(stats.employees, start=1):
        status = "" if emp.is_active else " <i>(nofaol)</i>"
        lines.append(f"{index}. <b>{html.escape(emp.full_name)}</b>{status} — {emp.count} ta baho")
        if emp.count:
            lines.append(
                f"    ⏱ Muddat: <b>{fmt_score(emp.avg_timing)}</b> | "
                f"⭐️ Sifat: <b>{fmt_score(emp.avg_quality)}</b>"
            )

    lines += ["", "🏢 <b>Ish joyi bo'yicha</b>"]
    lines += [f"• {html.escape(name)}: {count}" for name, count in stats.by_workplace]

    lines += ["", "🗂 <b>Funksiyalar bo'yicha</b>"]
    lines += [f"• {html.escape(name)}: {count}" for name, count in stats.by_function]
    return "\n".join(lines)


@router.message(Command("stats"))
async def cmd_stats(message: Message, session: AsyncSession) -> None:
    stats = await repo.get_stats(session)
    for chunk in split_message(format_stats(stats)):
        await message.answer(chunk)


# --- /export ------------------------------------------------------------------


@router.message(Command("export"))
async def cmd_export(message: Message, session: AsyncSession, settings: Settings) -> None:
    rows = await repo.list_feedback_with_employee(session)
    if not rows:
        await message.answer(texts.EXPORT_EMPTY)
        return
    progress = await message.answer(texts.EXPORT_PREPARING)
    content = build_feedback_xlsx(rows, settings.timezone)
    stamp = datetime.now(ZoneInfo(settings.timezone)).strftime("%Y%m%d_%H%M")
    await message.answer_document(
        BufferedInputFile(content, filename=f"baholash_{stamp}.xlsx"),
        caption=texts.EXPORT_CAPTION.format(count=len(rows)),
    )
    with suppress(TelegramBadRequest):
        await progress.delete()


# --- /employees -----------------------------------------------------------------


async def _employees_view(session: AsyncSession) -> tuple[str, InlineKeyboardMarkup]:
    employees = await repo.list_employees(session, active_only=False)
    text = texts.EMPLOYEES_ADMIN if employees else texts.EMPLOYEES_ADMIN_EMPTY
    return text, kb.employees_admin_kb(employees)


async def _refresh_list(callback: CallbackQuery, session: AsyncSession) -> None:
    if not isinstance(callback.message, Message):
        return
    text, markup = await _employees_view(session)
    with suppress(TelegramBadRequest):
        await callback.message.edit_text(text, reply_markup=markup)


@router.message(Command("employees"))
async def cmd_employees(message: Message, session: AsyncSession) -> None:
    text, markup = await _employees_view(session)
    await message.answer(text, reply_markup=markup)


@router.callback_query(AdminEmpCb.filter(F.action == "toggle"))
async def on_toggle_employee(
    callback: CallbackQuery, callback_data: AdminEmpCb, session: AsyncSession
) -> None:
    employee = await repo.toggle_employee(session, callback_data.id)
    if employee is None:
        await callback.answer(texts.EMPLOYEE_NOT_FOUND, show_alert=True)
    else:
        template = texts.EMPLOYEE_ACTIVATED if employee.is_active else texts.EMPLOYEE_DEACTIVATED
        await callback.answer(template.format(name=employee.full_name))
        logger.info("Admin %s toggled employee %s -> %s", callback.from_user.id, employee.id, employee.is_active)
    await _refresh_list(callback, session)


@router.callback_query(AdminEmpCb.filter(F.action == "delete"))
async def on_delete_employee(
    callback: CallbackQuery, callback_data: AdminEmpCb, session: AsyncSession
) -> None:
    result, name = await repo.delete_employee(session, callback_data.id)
    if result is repo.DeleteResult.NOT_FOUND:
        await callback.answer(texts.EMPLOYEE_NOT_FOUND, show_alert=True)
    elif result is repo.DeleteResult.DEACTIVATED:
        await callback.answer(texts.EMPLOYEE_HAS_FEEDBACK.format(name=name), show_alert=True)
    else:
        await callback.answer(texts.EMPLOYEE_DELETED.format(name=name))
    logger.info("Admin %s delete employee %s: %s", callback.from_user.id, callback_data.id, result.value)
    await _refresh_list(callback, session)


@router.callback_query(AdminEmpCb.filter(F.action == "add"))
async def on_add_employee(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AdminStates.add_employee)
    await callback.answer()
    if callback.message:
        await callback.message.answer(texts.ASK_NEW_EMPLOYEE, reply_markup=kb.admin_cancel_kb())


@router.callback_query(AdminEmpCb.filter(F.action == "cancel_add"))
async def on_cancel_add(callback: CallbackQuery, state: FSMContext) -> None:
    if await state.get_state() == AdminStates.add_employee.state:
        await state.clear()
    await callback.answer()
    if isinstance(callback.message, Message):
        with suppress(TelegramBadRequest):
            await callback.message.edit_text(texts.EMPLOYEE_ADD_CANCELLED)


@router.message(AdminStates.add_employee, F.text & ~F.text.startswith("/"))
async def on_new_employee_name(message: Message, state: FSMContext, session: AsyncSession) -> None:
    name = validate_full_name(message.text)
    if name is None:
        await message.answer(texts.INVALID_NAME, reply_markup=kb.admin_cancel_kb())
        return
    employee, created = await repo.add_employee(session, name)
    if not created:
        await message.answer(
            texts.EMPLOYEE_EXISTS.format(name=html.escape(employee.full_name)),
            reply_markup=kb.admin_cancel_kb(),
        )
        return
    await state.clear()
    logger.info("Admin %s added employee %s", message.from_user.id if message.from_user else "?", employee.id)
    await message.answer(texts.EMPLOYEE_ADDED.format(name=html.escape(employee.full_name)))
    text, markup = await _employees_view(session)
    await message.answer(text, reply_markup=markup)


@router.message(AdminStates.add_employee)
async def on_new_employee_wrong_input(message: Message) -> None:
    await message.answer(texts.TEXT_EXPECTED, reply_markup=kb.admin_cancel_kb())
