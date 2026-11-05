"""So'rovnoma klaviaturalari. Har bir qadamda "Orqaga" va "Bekor qilish" bor."""
from __future__ import annotations

from collections.abc import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts
from bot.db.models import Employee
from bot.keyboards.callbacks import BEGIN, EmployeeCb, FunctionCb, NavCb, ScoreCb, WorkplaceCb


def _nav_row(builder: InlineKeyboardBuilder) -> None:
    builder.row(
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=NavCb(action="back").pack()),
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=NavCb(action="cancel").pack()),
    )


def greeting_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=texts.BTN_START, callback_data=BEGIN)
    builder.row(
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=NavCb(action="cancel").pack())
    )
    return builder.as_markup()


def nav_kb(*, skip: bool = False) -> InlineKeyboardMarkup:
    """Matn kiritiladigan qadamlar uchun."""
    builder = InlineKeyboardBuilder()
    if skip:
        builder.button(text=texts.BTN_SKIP, callback_data=NavCb(action="skip"))
    _nav_row(builder)
    return builder.as_markup()


def workplace_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, (code, name) in enumerate(texts.WORKPLACES.items(), start=1):
        builder.button(text=f"{index}. {name}", callback_data=WorkplaceCb(code=code))
    builder.adjust(1)
    _nav_row(builder)
    return builder.as_markup()


def employees_kb(employees: Sequence[Employee]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for employee in employees:
        builder.button(text=employee.full_name, callback_data=EmployeeCb(id=employee.id))
    builder.adjust(1)
    _nav_row(builder)
    return builder.as_markup()


def functions_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for code, name in texts.FUNCTIONS.items():
        builder.button(text=name, callback_data=FunctionCb(code=code))
    builder.adjust(2)
    _nav_row(builder)
    return builder.as_markup()


def score_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for value, label in texts.SCORES.items():
        builder.button(text=f"{value} {label}", callback_data=ScoreCb(value=value))
    builder.adjust(1)
    _nav_row(builder)
    return builder.as_markup()
