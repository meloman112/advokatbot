from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from aiogram import BaseMiddleware

from src.repository.user import UserRepository
from src.utils.enum import LanguageEnum
from src.utils.texts import load_json_text

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from aiogram.types import TelegramObject, User


class TextsDepMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")
        lang: str = LanguageEnum.RU
        if tg_user is not None:
            user = await UserRepository.get_by_tg_id(session=data["session"], tg_id=tg_user.id)
            if user is not None:
                lang = user.lang
        data["lang"] = lang
        data["texts"] = await load_json_text(lang)
        return await handler(event, data)
