"""Admin klaviaturalari."""
from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.db.models import Employee
from bot.keyboards.callbacks import AdminEmpCb


def employees_admin_kb(employees: Sequence[Employee]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for employee in employees:
        mark = "🟢" if employee.is_active else "⚪️"
        builder.row(
            InlineKeyboardButton(
                text=f"{mark} {employee.full_name}",
                callback_data=AdminEmpCb(action="toggle", id=employee.id).pack(),
            ),
            InlineKeyboardButton(
                text="🗑", callback_data=AdminEmpCb(action="delete", id=employee.id).pack()
            ),
        )
    builder.row(
        InlineKeyboardButton(
            text=texts.BTN_ADD_EMPLOYEE, callback_data=AdminEmpCb(action="add").pack()
        )
    )
    return builder.as_markup()


def admin_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_ADMIN_CANCEL, callback_data=AdminEmpCb(action="cancel_add"))
    return builder.as_markup()
