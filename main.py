"""Kirish nuqtasi: migratsiyalar → bot polling → graceful shutdown."""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramUnauthorizedError
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from alembic import command
from alembic.config import Config as AlembicConfig
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from bot import texts
from bot.config import BASE_DIR, Settings, load_settings
from bot.db import create_engine, create_session_pool
from bot.handlers import get_routers
from bot.handlers.errors import on_error
from bot.middlewares import DbSessionMiddleware

logger = logging.getLogger("bot")


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # aiogram'ning har bir update haqidagi INFO loglari juda ko'p
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def run_migrations() -> None:
    """Alembic orqali DB sxemasini oxirgi versiyaga yangilaydi (event loop'dan oldin)."""
    cfg = AlembicConfig(str(BASE_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BASE_DIR / "alembic"))
    command.upgrade(cfg, "head")


async def set_commands(bot: Bot, settings: Settings) -> None:
    user_commands = [
        BotCommand(command="start", description=texts.CMD_START),
        BotCommand(command="cancel", description=texts.CMD_CANCEL),
        BotCommand(command="help", description=texts.CMD_HELP),
    ]
    admin_commands = user_commands + [
        BotCommand(command="stats", description=texts.CMD_STATS),
        BotCommand(command="export", description=texts.CMD_EXPORT),
        BotCommand(command="employees", description=texts.CMD_EMPLOYEES),
    ]
    await bot.set_my_commands(user_commands, scope=BotCommandScopeDefault())
    for admin_id in settings.admin_ids:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramAPIError as exc:
            # Admin hali botga /start bosmagan bo'lsa, chat topilmaydi
            logger.warning("Could not set admin commands for %s: %s", admin_id, exc)


def create_dispatcher(settings: Settings, session_pool: async_sessionmaker[AsyncSession]) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp["settings"] = settings  # handlerlarga `settings` argumenti sifatida uzatiladi
    dp.update.middleware(DbSessionMiddleware(session_pool))
    dp.include_routers(*get_routers())
    dp.errors.register(on_error)
    return dp


async def run_bot(settings: Settings) -> None:
    engine: AsyncEngine = create_engine(settings.db_url)
    session_pool = create_session_pool(engine)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = create_dispatcher(settings, session_pool)

    async def on_startup() -> None:
        me = await bot.get_me()
        logger.info("Bot started as @%s (id=%s)", me.username, me.id)
        try:
            await set_commands(bot, settings)
        except TelegramAPIError:
            logger.exception("Failed to set bot commands")

    async def on_shutdown() -> None:
        logger.info("Shutting down...")

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        # start_polling SIGINT/SIGTERM signallarini o'zi ushlaydi va to'g'ri to'xtaydi
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        await engine.dispose()
        logger.info("Bot stopped, connections closed")


def main() -> None:
    try:
        settings = load_settings()
    except RuntimeError as exc:
        print(f"Konfiguratsiya xatosi: {exc}", file=sys.stderr)
        sys.exit(1)

    setup_logging(settings.log_level)
    try:
        logger.info("Applying database migrations...")
        run_migrations()
        asyncio.run(run_bot(settings))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped by signal")
    except TelegramUnauthorizedError:
        logger.error("Telegram BOT_TOKEN ni rad etdi — .env dagi tokenni tekshiring")
        sys.exit(1)
    except Exception:
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
