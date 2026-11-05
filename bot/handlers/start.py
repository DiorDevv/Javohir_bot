"""/start, /cancel, /help — har qanday holatda ishlaydi."""
from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot import texts
from bot.config import Settings
from bot.handlers.common import drop_prompt_markup, send_step
from bot.states import Survey

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, bot: Bot, session: AsyncSession) -> None:
    """/start qayta bosilsa ham jarayon boshidan boshlanadi."""
    await drop_prompt_markup(bot, message.chat.id, state)
    await state.clear()
    await send_step(bot, message.chat.id, state, Survey.greeting, session)


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, bot: Bot) -> None:
    await drop_prompt_markup(bot, message.chat.id, state)
    await state.clear()
    await message.answer(texts.CANCELLED)


@router.message(Command("help"))
async def cmd_help(message: Message, settings: Settings) -> None:
    is_admin = message.from_user is not None and message.from_user.id in settings.admin_ids
    await message.answer(texts.HELP + (texts.HELP_ADMIN if is_admin else ""))
