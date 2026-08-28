from __future__ import annotations

from typing import TYPE_CHECKING

from src.config import settings
from src.repository.user import UserRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def is_admin(session: AsyncSession, tg_id: int) -> bool:
    if tg_id == settings.bot.superadmin_id:
        return True
    user = await UserRepository.get_by_tg_id(session=session, tg_id=tg_id)
    return user is not None and user.is_admin
