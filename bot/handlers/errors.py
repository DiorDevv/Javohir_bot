"""Global xatolik ushlagich: logga yozadi va foydalanuvchiga xabar beradi."""
from __future__ import annotations

import logging

from aiogram.types import ErrorEvent

from bot import texts

logger = logging.getLogger(__name__)


async def on_error(event: ErrorEvent) -> bool:
    logger.error(
        "Unhandled error while processing update %s",
        event.update.update_id,
        exc_info=event.exception,
    )
    update = event.update
    try:
        if update.message is not None:
            await update.message.answer(texts.UNEXPECTED_ERROR)
        elif update.callback_query is not None:
            await update.callback_query.answer(texts.UNEXPECTED_ERROR_SHORT, show_alert=True)
    except Exception:  # noqa: BLE001 — xabar yuborib bo'lmasa ham bot to'xtamasligi kerak
        logger.warning("Failed to notify user about error", exc_info=True)
    return True
