"""So'rovnoma qadamlarini chizish va navigatsiya (Orqaga) uchun umumiy funksiyalar."""
from __future__ import annotations

import html
from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.db import repo
from bot.keyboards import survey as kb
from bot.states import Survey

# FSM data'dagi oxirgi savol xabari ID si (eski tugmalarni o'chirish uchun)
PROMPT_KEY = "prompt_msg_id"

# "⬅️ Orqaga" bosilganda qaysi qadamga qaytiladi
PREVIOUS_STEP: dict[str, State] = {
    Survey.name.state: Survey.greeting,
    Survey.workplace.state: Survey.name,
    Survey.employee.state: Survey.workplace,
    Survey.function.state: Survey.employee,
    Survey.function_other.state: Survey.function,
    Survey.timing_score.state: Survey.function,
    Survey.timing_reason.state: Survey.timing_score,
    Survey.quality_score.state: Survey.timing_reason,
    Survey.quality_reason.state: Survey.quality_score,
    Survey.suggestions.state: Survey.quality_reason,
}

# Matn kutiladigan va tugma kutiladigan holatlar
TEXT_STATES: tuple[State, ...] = (
    Survey.name,
    Survey.function_other,
    Survey.timing_reason,
    Survey.quality_reason,
    Survey.suggestions,
)
BUTTON_STATES: tuple[State, ...] = (
    Survey.greeting,
    Survey.workplace,
    Survey.employee,
    Survey.function,
    Survey.timing_score,
    Survey.quality_score,
)
TEXT_STATE_NAMES: frozenset[str] = frozenset(s.state for s in TEXT_STATES)
_STATES_BY_NAME: dict[str, State] = {s.state: s for s in (*TEXT_STATES, *BUTTON_STATES)}


def state_by_name(name: str | None) -> State | None:
    return _STATES_BY_NAME.get(name) if name else None


def callback_chat_id(callback: CallbackQuery) -> int:
    return callback.message.chat.id if callback.message else callback.from_user.id


async def drop_prompt_markup(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """Oldingi savol xabaridagi tugmalarni olib tashlaydi (eski tugmalar bosilmasligi uchun)."""
    message_id = (await state.get_data()).get(PROMPT_KEY)
    if message_id:
        with suppress(TelegramBadRequest):
            await bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id, reply_markup=None)


async def mark_choice(callback: CallbackQuery, label: str) -> None:
    """Tanlangan javobni savol ostiga yozib, tugmalarni olib tashlaydi."""
    message = callback.message
    if isinstance(message, Message):
        with suppress(TelegramBadRequest):
            await message.edit_text(
                f"{message.html_text}\n\n✅ <b>{html.escape(label)}</b>", reply_markup=None
            )


async def _build_step(
    step: State, session: AsyncSession, *, intro: bool
) -> tuple[str, InlineKeyboardMarkup] | None:
    """Qadam uchun (matn, klaviatura). Xodimlar ro'yxati bo'sh bo'lsa — None."""
    if step == Survey.greeting:
        return texts.GREETING, kb.greeting_kb()
    if step == Survey.name:
        return texts.ASK_NAME, kb.nav_kb()
    if step == Survey.workplace:
        return texts.ASK_WORKPLACE, kb.workplace_kb()
    if step == Survey.employee:
        employees = await repo.list_employees(session)
        if not employees:
            return None
        return texts.ASK_EMPLOYEE, kb.employees_kb(employees)
    if step == Survey.function:
        return texts.ASK_FUNCTION, kb.functions_kb()
    if step == Survey.function_other:
        return texts.ASK_FUNCTION_OTHER, kb.nav_kb()
    if step == Survey.timing_score:
        text = f"{texts.CONTINUE}\n\n{texts.Q_TIMING}" if intro else texts.Q_TIMING
        return text, kb.score_kb()
    if step in (Survey.timing_reason, Survey.quality_reason):
        return texts.ASK_REASON, kb.nav_kb()
    if step == Survey.quality_score:
        return texts.Q_QUALITY, kb.score_kb()
    if step == Survey.suggestions:
        return texts.ASK_SUGGESTIONS, kb.nav_kb(skip=True)
    raise ValueError(f"Noma'lum qadam: {step}")


async def send_step(
    bot: Bot,
    chat_id: int,
    state: FSMContext,
    step: State,
    session: AsyncSession,
    *,
    intro: bool = False,
) -> None:
    """Holatni `step` ga o'tkazadi va shu qadam savolini yuboradi."""
    built = await _build_step(step, session, intro=intro)
    await drop_prompt_markup(bot, chat_id, state)
    if built is None:
        await state.clear()
        await bot.send_message(chat_id, texts.NO_EMPLOYEES)
        return
    text, markup = built
    await state.set_state(step)
    sent = await bot.send_message(chat_id, text, reply_markup=markup)
    await state.update_data({PROMPT_KEY: sent.message_id})
