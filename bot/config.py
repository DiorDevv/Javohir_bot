"""Sozlamalar: .env fayli yoki muhit o'zgaruvchilaridan o'qiladi."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DEFAULT_DB_URL = "sqlite+aiosqlite:///data/bot.db"


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    db_url: str
    admin_ids: frozenset[int]
    cooldown_hours: int
    timezone: str
    log_level: str


def get_db_url() -> str:
    """Alembic ham ishlatadi, shuning uchun BOT_TOKEN talab qilinmaydi."""
    return os.getenv("DB_URL", "").strip() or DEFAULT_DB_URL


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if not part.lstrip("-").isdigit():
            raise RuntimeError(f"ADMIN_IDS noto'g'ri qiymatga ega: {part!r}")
        ids.add(int(part))
    return frozenset(ids)


def load_settings() -> Settings:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("BOT_TOKEN ko'rsatilmagan (.env faylini tekshiring)")

    cooldown_raw = os.getenv("FEEDBACK_COOLDOWN_HOURS", "24").strip() or "24"
    try:
        cooldown = max(0, int(cooldown_raw))
    except ValueError as exc:
        raise RuntimeError("FEEDBACK_COOLDOWN_HOURS butun son bo'lishi kerak") from exc

    return Settings(
        bot_token=token,
        db_url=get_db_url(),
        admin_ids=_parse_admin_ids(os.getenv("ADMIN_IDS", "")),
        cooldown_hours=cooldown,
        timezone=os.getenv("TIMEZONE", "Asia/Tashkent").strip() or "Asia/Tashkent",
        log_level=os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO",
    )
