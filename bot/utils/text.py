"""Matn bilan ishlash yordamchilari."""
from __future__ import annotations

TELEGRAM_LIMIT = 4096


def split_message(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Uzun matnni Telegram chegarasiga sig'adigan bo'laklarga (qatorlar bo'yicha) ajratadi."""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit and current:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def fmt_score(value: float | None) -> str:
    return "—" if value is None else f"{value:.2f}"
