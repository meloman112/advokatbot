from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramBadRequest

if TYPE_CHECKING:
    from aiogram.types import InlineKeyboardMarkup, Message


async def edit_text(message: Message, text: str, reply_markup: InlineKeyboardMarkup | None = None) -> None:
    """Повторное нажатие на ту же кнопку присылает тот же текст — Telegram отвечает ошибкой, это не проблема."""
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e):
            raise
