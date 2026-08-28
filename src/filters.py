from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram.filters import Filter

from src.utils.access import is_admin

if TYPE_CHECKING:
    from aiogram.types import TelegramObject
    from sqlalchemy.ext.asyncio import AsyncSession


class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject, session: AsyncSession) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        return await is_admin(session=session, tg_id=user.id)
