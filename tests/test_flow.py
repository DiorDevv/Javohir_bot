"""End-to-end: Dispatcher'ga update'lar beriladi, Telegram API esa soxta sessiya bilan almashtiriladi."""
from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime
from itertools import count
from typing import Any

import pytest
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.methods import AnswerCallbackQuery, GetMe, SendDocument, SendMessage, TelegramMethod
from aiogram.types import CallbackQuery, Chat, Message, Update, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import texts
from bot.config import Settings
from bot.db import Employee, Feedback
from bot.handlers import get_routers
from main import create_dispatcher

ADMIN_ID = 900
USER_ID = 100


class FakeSession(BaseSession):
    """Telegram'ga so'rov yubormaydi, faqat yozib boradi."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []
        self._ids = count(1000)

    async def close(self) -> None:
        pass

    async def stream_content(self, *args: Any, **kwargs: Any) -> AsyncGenerator[bytes, None]:
        yield b""

    async def make_request(self, bot: Bot, method: TelegramMethod[Any], timeout: int | None = None) -> Any:
        self.requests.append(method)
        if isinstance(method, GetMe):
            return User(id=1, is_bot=True, first_name="Bot", username="test_bot")
        if isinstance(method, (SendMessage, SendDocument)):
            return Message(
                message_id=next(self._ids),
                date=datetime.now(),
                chat=Chat(id=method.chat_id, type="private"),
                text=getattr(method, "text", None),
            )
        return True


class Harness:
    def __init__(self, pool: async_sessionmaker[AsyncSession]) -> None:
        self.session = FakeSession()
        self.bot = Bot("42:TEST", session=self.session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        settings = Settings(
            bot_token="42:TEST",
            db_url="sqlite+aiosqlite:///:memory:",
            admin_ids=frozenset({ADMIN_ID}),
            cooldown_hours=24,
            timezone="Asia/Tashkent",
            log_level="INFO",
        )
        self.dp = create_dispatcher(settings, pool)
        self._update_ids = count(1)

    def _user(self, user_id: int) -> User:
        return User(id=user_id, is_bot=False, first_name="Test", username=f"u{user_id}")

    async def text(self, text: str, user_id: int = USER_ID) -> None:
        self.session.requests.clear()
        message = Message(
            message_id=next(self._update_ids),
            date=datetime.now(),
            chat=Chat(id=user_id, type="private"),
            from_user=self._user(user_id),
            text=text,
        )
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), message=message))

    async def press(self, data: str, user_id: int = USER_ID) -> None:
        self.session.requests.clear()
        message = Message(
            message_id=1, date=datetime.now(), chat=Chat(id=user_id, type="private"), text="prompt"
        )
        callback = CallbackQuery(
            id=str(next(self._update_ids)),
            from_user=self._user(user_id),
            chat_instance="ci",
            data=data,
            message=message,
        )
        await self.dp.feed_update(self.bot, Update(update_id=next(self._update_ids), callback_query=callback))

    @property
    def sent(self) -> list[str]:
        return [r.text for r in self.session.requests if isinstance(r, SendMessage)]

    @property
    def alerts(self) -> list[str | None]:
        return [r.text for r in self.session.requests if isinstance(r, AnswerCallbackQuery)]


@pytest.fixture
async def h(session_pool: async_sessionmaker[AsyncSession]) -> AsyncGenerator[Harness, None]:
    yield Harness(session_pool)
    # Routerlar modul darajasida — keyingi test yangi Dispatcher'ga ulay olishi uchun ajratamiz
    for router in get_routers():
        router._parent_router = None


async def _employee_id(pool: async_sessionmaker[AsyncSession], name: str) -> int:
    async with pool() as s:
        return (await s.scalars(select(Employee.id).where(Employee.full_name == name))).one()


async def test_full_flow(h: Harness, session_pool: async_sessionmaker[AsyncSession]) -> None:
    emp_id = await _employee_id(session_pool, "Yodgorova Xolida")

    await h.text("/start")
    assert h.sent == [texts.GREETING]

    await h.press("survey:begin")
    assert h.sent == [texts.ASK_NAME]

    await h.text("Vali")  # 1 so'z — noto'g'ri
    assert h.sent == [texts.INVALID_NAME, texts.ASK_NAME]

    await h.text("Aliyev Vali")
    assert h.sent == [texts.ASK_WORKPLACE]

    await h.text("1")  # tugma kutilgan joyda matn
    assert h.sent == [texts.BUTTON_EXPECTED, texts.ASK_WORKPLACE]

    await h.press("wp:city")
    assert h.sent == [texts.ASK_EMPLOYEE]

    await h.press(f"emp:{emp_id}")
    assert h.sent == [texts.ASK_FUNCTION]

    await h.press("fn:other")
    assert h.sent == [texts.ASK_FUNCTION_OTHER]

    await h.press("nav:back")
    assert h.sent == [texts.ASK_FUNCTION]

    await h.press("fn:other")
    await h.text("Malaka oshirish")
    assert h.sent == [f"{texts.CONTINUE}\n\n{texts.Q_TIMING}"]

    await h.press("score:5")
    assert h.sent == [texts.ASK_REASON]

    await h.press("score:3")  # matn kutilgan joyda tugma
    assert h.alerts == [texts.TEXT_EXPECTED_ALERT]

    await h.text("   ")
    await h.text("Hammasi o'z vaqtida bajarildi")
    assert h.sent == [texts.Q_QUALITY]

    await h.press("score:4")
    await h.text("Xushmuomala")
    assert h.sent == [texts.ASK_SUGGESTIONS]

    await h.press("nav:skip")
    assert h.sent == [texts.THANKS]

    async with session_pool() as s:
        fb = (await s.scalars(select(Feedback))).one()
    assert (fb.full_name, fb.workplace, fb.employee_id) == ("Aliyev Vali", "Toshkent shahar Bosh boshqarmasi", emp_id)
    assert fb.function == "Boshqa: Malaka oshirish"
    assert (fb.timing_score, fb.quality_score, fb.suggestions) == (5, 4, None)
    assert fb.timing_reason == "Hammasi o'z vaqtida bajarildi"

    # Spamdan himoya: shu xodimni qayta baholab bo'lmaydi
    await h.text("/start")
    await h.press("survey:begin")
    await h.text("Aliyev Vali")
    await h.press("wp:office")
    await h.press(f"emp:{emp_id}")
    assert h.alerts == [texts.COOLDOWN_ALERT.format(hours=24)]
    assert h.sent == []

    # Bekor qilish
    await h.press("nav:cancel")
    assert h.sent == [texts.CANCELLED]
    await h.press("wp:office")  # eski tugma
    assert h.alerts == [texts.NO_ACTIVE_SURVEY]


async def test_admin_commands(h: Harness) -> None:
    await h.text("/stats", user_id=USER_ID)  # oddiy foydalanuvchi
    assert h.sent == [texts.NO_ACTIVE_SURVEY]

    await h.text("/stats", user_id=ADMIN_ID)
    assert h.sent == [texts.STATS_EMPTY]

    await h.text("/export", user_id=ADMIN_ID)
    assert h.sent == [texts.EXPORT_EMPTY]

    await h.text("/employees", user_id=ADMIN_ID)
    assert h.sent == [texts.EMPLOYEES_ADMIN]

    await h.press("adm:add:0", user_id=ADMIN_ID)
    await h.text("Aliyeva Malika", user_id=ADMIN_ID)
    assert h.sent[0] == texts.EMPLOYEE_ADDED.format(name="Aliyeva Malika")
