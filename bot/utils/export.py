"""Javoblarni Excel (.xlsx) faylga eksport qilish."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from io import BytesIO
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from bot.db.models import Feedback

# (sarlavha, ustun kengligi)
COLUMNS: list[tuple[str, int]] = [
    ("ID", 6),
    ("Sana va vaqt", 18),
    ("Telegram ID", 14),
    ("Username", 16),
    ("F.I.Sh (ishtirokchi)", 26),
    ("Ish joyi", 30),
    ("Baholangan xodim", 26),
    ("Funksiya", 24),
    ("Muddat bahosi", 10),
    ("Muddat — sabab", 40),
    ("Sifat bahosi", 10),
    ("Sifat — sabab", 40),
    ("Takliflar", 50),
]


def _local_naive(dt: datetime, tz: ZoneInfo) -> datetime:
    """Excel vaqt mintaqasini qo'llab-quvvatlamaydi — mahalliy vaqtga o'tkazib, tz olib tashlanadi."""
    if dt.tzinfo is None:  # SQLite naive UTC qaytaradi
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(tz).replace(tzinfo=None)


def build_feedback_xlsx(rows: Sequence[tuple[Feedback, str]], tz_name: str) -> bytes:
    tz = ZoneInfo(tz_name)
    wb = Workbook()
    ws = wb.active
    ws.title = "Baholashlar"

    ws.append([title for title, _ in COLUMNS])
    header_fill = PatternFill("solid", fgColor="DDEBF7")
    for index, (_, width) in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=index)
        cell.font = Font(bold=True)
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(index)].width = width

    for fb, employee_name in rows:
        ws.append(
            [
                fb.id,
                _local_naive(fb.created_at, tz),
                fb.telegram_id,
                f"@{fb.username}" if fb.username else "",
                fb.full_name,
                fb.workplace,
                employee_name,
                fb.function,
                fb.timing_score,
                fb.timing_reason,
                fb.quality_score,
                fb.quality_reason,
                fb.suggestions or "",
            ]
        )

    wrap = Alignment(vertical="top", wrap_text=True)
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
        row[1].number_format = "dd.mm.yyyy hh:mm"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
