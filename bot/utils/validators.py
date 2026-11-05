"""Foydalanuvchi kiritgan matnlarni tekshirish."""
from __future__ import annotations

import re
from dataclasses import dataclass

NAME_MAX_LEN = 100
FUNCTION_MAX_LEN = 200
REASON_MAX_LEN = 1000
SUGGESTION_MAX_LEN = 2000

# So'z: faqat harflar (lotin/kirill), o'zbekcha tutuq belgilari (O'ktam, G'ulom) va chiziqcha
_APOSTROPHES = "'’ʻʼ`‘"
_WORD_RE = re.compile(rf"^[^\W\d_]+(?:[{_APOSTROPHES}-][^\W\d_]+)*[{_APOSTROPHES}]?$")


def validate_full_name(raw: str | None) -> str | None:
    """Kamida 2 so'z, faqat harflar. To'g'ri bo'lsa — normallashtirilgan ism, aks holda None."""
    if not raw:
        return None
    words = raw.split()
    if len(words) < 2:
        return None
    if not all(_WORD_RE.match(word) for word in words):
        return None
    name = " ".join(words)
    if len(name) > NAME_MAX_LEN:
        return None
    return name


@dataclass(frozen=True, slots=True)
class TextCheck:
    value: str | None
    error: str | None  # "empty" | "too_long" | None

    @property
    def ok(self) -> bool:
        return self.error is None


def check_text(raw: str | None, max_len: int) -> TextCheck:
    """Erkin matn: bo'sh bo'lmasligi va `max_len` dan oshmasligi kerak."""
    value = (raw or "").strip()
    if not value:
        return TextCheck(None, "empty")
    if len(value) > max_len:
        return TextCheck(None, "too_long")
    return TextCheck(value, None)
