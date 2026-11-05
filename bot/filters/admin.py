"""Admin filtri: foydalanuvchi ADMIN_IDS ro'yxatida bo'lishi kerak."""
from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import CallbackQuery, Message

from bot.config import Settings


class IsAdmin(Filter):
    async def __call__(self, event: Message | CallbackQuery, settings: Settings) -> bool:
        user = event.from_user
        return user is not None and user.id in settings.admin_ids
