"""Inline tugmalar uchun callback_data fabrikalari."""
from __future__ import annotations

from aiogram.filters.callback_data import CallbackData

BEGIN = "survey:begin"


class NavCb(CallbackData, prefix="nav"):
    action: str  # back | cancel | skip


class WorkplaceCb(CallbackData, prefix="wp"):
    code: str


class EmployeeCb(CallbackData, prefix="emp"):
    id: int


class FunctionCb(CallbackData, prefix="fn"):
    code: str


class ScoreCb(CallbackData, prefix="score"):
    value: int


class AdminEmpCb(CallbackData, prefix="adm"):
    action: str  # toggle | delete | add | cancel_add
    id: int = 0
