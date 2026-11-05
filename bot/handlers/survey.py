"""So'rovnoma oqimi: ism → ish joyi → xodim → funksiya → 2 ta baho (+sabab) → takliflar."""
from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import CallbackQuery, Message, User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.config import Settings
from bot.db import repo
from bot.handlers.common import (
    BUTTON_STATES,
    PREVIOUS_STEP,
    TEXT_STATE_NAMES,
    TEXT_STATES,
    callback_chat_id,
    drop_prompt_markup,
    mark_choice,
    send_step,
    state_by_name,
)
from bot.keyboards.callbacks import BEGIN, EmployeeCb, FunctionCb, NavCb, ScoreCb, WorkplaceCb
from bot.states import Survey
from bot.utils.validators import (
    FUNCTION_MAX_LEN,
    REASON_MAX_LEN,
    SUGGESTION_MAX_LEN,
    TextCheck,
    check_text,
    validate_full_name,
)

logger = logging.getLogger(__name__)
router = Router(name="survey")

# Oddiy matn (buyruq emas)
PLAIN_TEXT = F.text & ~F.text.startswith("/")

REQUIRED_KEYS = (
    "full_name",
    "workplace",
    "employee_id",
    "function",
    "timing_score",
    "timing_reason",
    "quality_score",
    "quality_reason",
)


async def _reask(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession, step: State, error: str
) -> None:
    """Xato xabarini chiqarib, shu qadam savolini qayta beradi."""
    await message.answer(error)
    await send_step(bot, message.chat.id, state, step, session)


def _text_error(check: TextCheck, limit: int) -> str:
    return texts.TOO_LONG.format(limit=limit) if check.error == "too_long" else texts.EMPTY_TEXT


# --- Navigatsiya: Orqaga / Bekor qilish -------------------------------------


@router.callback_query(StateFilter(Survey), NavCb.filter(F.action == "cancel"))
async def on_cancel(callback: CallbackQuery, state: FSMContext, bot: Bot) -> None:
    chat_id = callback_chat_id(callback)
    await drop_prompt_markup(bot, chat_id, state)
    await state.clear()
    await callback.answer()
    await bot.send_message(chat_id, texts.CANCELLED)


@router.callback_query(StateFilter(Survey), NavCb.filter(F.action == "back"))
async def on_back(
    callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    current = await state.get_state()
    previous = PREVIOUS_STEP.get(current or "")
    await callback.answer()
    if previous is None:
        return
    await send_step(bot, callback_chat_id(callback), state, previous, session)


# --- 1. Salomlashish ----------------------------------------------------------


@router.callback_query(Survey.greeting, F.data == BEGIN)
async def on_begin(
    callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    await mark_choice(callback, texts.BTN_START)
    await callback.answer()
    await send_step(bot, callback_chat_id(callback), state, Survey.name, session)


# --- 2. Ism-familiya ------------------------------------------------------------


@router.message(Survey.name, PLAIN_TEXT)
async def on_name(message: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    full_name = validate_full_name(message.text)
    if full_name is None:
        await _reask(message, state, bot, session, Survey.name, texts.INVALID_NAME)
        return
    await state.update_data(full_name=full_name)
    await send_step(bot, message.chat.id, state, Survey.workplace, session)


# --- 3. Ish joyi --------------------------------------------------------------


@router.callback_query(Survey.workplace, WorkplaceCb.filter())
async def on_workplace(
    callback: CallbackQuery,
    callback_data: WorkplaceCb,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    workplace = texts.WORKPLACES.get(callback_data.code)
    if workplace is None:
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await mark_choice(callback, workplace)
    await callback.answer()
    await state.update_data(workplace=workplace)
    await send_step(bot, callback_chat_id(callback), state, Survey.employee, session)


# --- 4. Xodim -------------------------------------------------------------------


@router.callback_query(Survey.employee, EmployeeCb.filter())
async def on_employee(
    callback: CallbackQuery,
    callback_data: EmployeeCb,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
    settings: Settings,
) -> None:
    employee = await repo.get_employee(session, callback_data.id)
    if employee is None or not employee.is_active:
        await callback.answer(texts.EMPLOYEE_UNAVAILABLE, show_alert=True)
        # Ro'yxat eskirgan bo'lishi mumkin — yangilangan ro'yxatni ko'rsatamiz
        await send_step(bot, callback_chat_id(callback), state, Survey.employee, session)
        return

    # Spamdan himoya: bitta xodimni N soatda bir marta
    if await repo.has_recent_feedback(
        session, callback.from_user.id, employee.id, settings.cooldown_hours
    ):
        await callback.answer(
            texts.COOLDOWN_ALERT.format(hours=settings.cooldown_hours), show_alert=True
        )
        return

    await mark_choice(callback, employee.full_name)
    await callback.answer()
    await state.update_data(employee_id=employee.id, employee_name=employee.full_name)
    await send_step(bot, callback_chat_id(callback), state, Survey.function, session)


# --- 5. Funksiya ------------------------------------------------------------------


@router.callback_query(Survey.function, FunctionCb.filter())
async def on_function(
    callback: CallbackQuery,
    callback_data: FunctionCb,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    name = texts.FUNCTIONS.get(callback_data.code)
    if name is None:
        await callback.answer(texts.STALE_BUTTON, show_alert=True)
        return
    await mark_choice(callback, name)
    await callback.answer()
    chat_id = callback_chat_id(callback)
    if callback_data.code == texts.FUNCTION_OTHER:
        await send_step(bot, chat_id, state, Survey.function_other, session)
        return
    await state.update_data(function=name)
    await send_step(bot, chat_id, state, Survey.timing_score, session, intro=True)


@router.message(Survey.function_other, PLAIN_TEXT)
async def on_function_other(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    check = check_text(message.text, FUNCTION_MAX_LEN)
    if not check.ok:
        await _reask(
            message, state, bot, session, Survey.function_other, _text_error(check, FUNCTION_MAX_LEN)
        )
        return
    await state.update_data(function=f"{texts.FUNCTION_OTHER_PREFIX}{check.value}")
    await send_step(bot, message.chat.id, state, Survey.timing_score, session, intro=True)


# --- 6–7. Baholar va sabablar --------------------------------------------------


@router.callback_query(Survey.timing_score, ScoreCb.filter())
async def on_timing_score(
    callback: CallbackQuery,
    callback_data: ScoreCb,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    await _save_score(callback, callback_data, state, "timing_score")
    await send_step(bot, callback_chat_id(callback), state, Survey.timing_reason, session)


@router.message(Survey.timing_reason, PLAIN_TEXT)
async def on_timing_reason(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    check = check_text(message.text, REASON_MAX_LEN)
    if not check.ok:
        await _reask(
            message, state, bot, session, Survey.timing_reason, _text_error(check, REASON_MAX_LEN)
        )
        return
    await state.update_data(timing_reason=check.value)
    await send_step(bot, message.chat.id, state, Survey.quality_score, session)


@router.callback_query(Survey.quality_score, ScoreCb.filter())
async def on_quality_score(
    callback: CallbackQuery,
    callback_data: ScoreCb,
    state: FSMContext,
    bot: Bot,
    session: AsyncSession,
) -> None:
    await _save_score(callback, callback_data, state, "quality_score")
    await send_step(bot, callback_chat_id(callback), state, Survey.quality_reason, session)


@router.message(Survey.quality_reason, PLAIN_TEXT)
async def on_quality_reason(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    check = check_text(message.text, REASON_MAX_LEN)
    if not check.ok:
        await _reask(
            message, state, bot, session, Survey.quality_reason, _text_error(check, REASON_MAX_LEN)
        )
        return
    await state.update_data(quality_reason=check.value)
    await send_step(bot, message.chat.id, state, Survey.suggestions, session)


async def _save_score(
    callback: CallbackQuery, callback_data: ScoreCb, state: FSMContext, key: str
) -> None:
    label = texts.SCORES.get(callback_data.value, "")
    await mark_choice(callback, f"{callback_data.value} {label}")
    await callback.answer()
    await state.update_data({key: callback_data.value})


# --- 8. Takliflar va yakun ------------------------------------------------------


@router.message(Survey.suggestions, PLAIN_TEXT)
async def on_suggestions(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession, settings: Settings
) -> None:
    check = check_text(message.text, SUGGESTION_MAX_LEN)
    if not check.ok:
        await _reask(
            message, state, bot, session, Survey.suggestions, _text_error(check, SUGGESTION_MAX_LEN)
        )
        return
    if message.from_user is None:
        return
    await _finish(bot, message.chat.id, message.from_user, state, session, settings, check.value)


@router.callback_query(Survey.suggestions, NavCb.filter(F.action == "skip"))
async def on_skip_suggestions(
    callback: CallbackQuery, state: FSMContext, bot: Bot, session: AsyncSession, settings: Settings
) -> None:
    await mark_choice(callback, texts.BTN_SKIP)
    await callback.answer()
    await _finish(
        bot, callback_chat_id(callback), callback.from_user, state, session, settings, None
    )


async def _finish(
    bot: Bot,
    chat_id: int,
    user: User,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
    suggestions: str | None,
) -> None:
    data = await state.get_data()
    if any(data.get(key) is None for key in REQUIRED_KEYS):
        logger.warning("Incomplete survey data for user %s: %s", user.id, list(data))
        await state.clear()
        await bot.send_message(chat_id, texts.SESSION_EXPIRED)
        return

    # Qayta tekshiruv: parallel ikki so'rovnoma orqali cheklovni aylanib o'tishning oldini olish
    if await repo.has_recent_feedback(session, user.id, data["employee_id"], settings.cooldown_hours):
        await drop_prompt_markup(bot, chat_id, state)
        await state.clear()
        await bot.send_message(chat_id, texts.COOLDOWN_FINAL)
        return

    try:
        feedback = await repo.create_feedback(
            session,
            telegram_id=user.id,
            username=user.username,
            full_name=data["full_name"],
            workplace=data["workplace"],
            employee_id=data["employee_id"],
            function=data["function"],
            timing_score=data["timing_score"],
            timing_reason=data["timing_reason"],
            quality_score=data["quality_score"],
            quality_reason=data["quality_reason"],
            suggestions=suggestions,
        )
    except SQLAlchemyError:
        logger.exception("Failed to save feedback for user %s", user.id)
        await bot.send_message(chat_id, texts.SAVE_ERROR)
        return  # holat saqlanib qoladi — foydalanuvchi qayta yuborishi mumkin

    logger.info(
        "Feedback #%s saved: user=%s employee=%s timing=%s quality=%s",
        feedback.id, user.id, data["employee_id"], data["timing_score"], data["quality_score"],
    )
    await drop_prompt_markup(bot, chat_id, state)
    await state.clear()
    await bot.send_message(chat_id, texts.THANKS)


# --- Noto'g'ri turdagi javoblar (eng oxirida ro'yxatdan o'tadi) ----------------


@router.message(StateFilter(*TEXT_STATES))
async def on_wrong_input_text_state(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """Matn kutilgan joyda stiker, rasm, buyruq va h.k. yuborildi."""
    step = state_by_name(await state.get_state())
    if step is not None:
        await _reask(message, state, bot, session, step, texts.TEXT_EXPECTED)


@router.message(StateFilter(*BUTTON_STATES))
async def on_wrong_input_button_state(
    message: Message, state: FSMContext, bot: Bot, session: AsyncSession
) -> None:
    """Tugma kutilgan joyda matn yozildi."""
    step = state_by_name(await state.get_state())
    if step is not None:
        await _reask(message, state, bot, session, step, texts.BUTTON_EXPECTED)


@router.callback_query(StateFilter(Survey))
async def on_unexpected_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Matn kutilgan joyda tugma bosildi yoki eski xabardagi tugma bosildi."""
    current = await state.get_state()
    text = texts.TEXT_EXPECTED_ALERT if current in TEXT_STATE_NAMES else texts.STALE_BUTTON
    await callback.answer(text, show_alert=True)


@router.callback_query()
async def on_callback_without_survey(callback: CallbackQuery) -> None:
    await callback.answer(texts.NO_ACTIVE_SURVEY, show_alert=True)


@router.message(StateFilter(None))
async def on_message_without_survey(message: Message) -> None:
    await message.answer(texts.NO_ACTIVE_SURVEY)
