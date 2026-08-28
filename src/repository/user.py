from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select

from src.core.models import UserOrm
from src.core.schemas import UserCreateS
from src.core.schemas.user import UserUpdateS
from src.repository.base import BaseRepository

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy import ScalarResult
    from sqlalchemy.ext.asyncio import AsyncSession

log = logging.getLogger(__name__)


class UserRepository(BaseRepository[UserOrm, UserCreateS, UserUpdateS]):
    model_class: type[UserOrm] = UserOrm

    @classmethod
    async def get_by_tg_id(cls, session: AsyncSession, tg_id: int) -> UserOrm | None:
        scalar_result: ScalarResult[UserOrm] = await cls._get_by_fields(session=session, tg_id=tg_id)
        user: UserOrm | None = scalar_result.one_or_none()
        return user

    @classmethod
    async def update_by_tg_id(cls, session: AsyncSession, tg_id: int, update_schema: UserUpdateS) -> None:
        await cls._update_by_filter_by(
            session=session,
            update_schema=update_schema,
            tg_id=tg_id,
        )

    @classmethod
    async def delete_by_tg_id(cls, session: AsyncSession, tg_id: int) -> None:
        await cls._delete_by_filter_by(session=session, tg_id=tg_id)

    @classmethod
    async def get_page(cls, session: AsyncSession, offset: int, limit: int) -> Sequence[UserOrm]:
        stmt = select(UserOrm).order_by(UserOrm.id.desc()).offset(offset).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def count(cls, session: AsyncSession) -> int:
        stmt = select(func.count()).select_from(UserOrm)
        return (await session.execute(stmt)).scalar_one()

    @classmethod
    async def get_admins(cls, session: AsyncSession) -> Sequence[UserOrm]:
        stmt = select(UserOrm).where(UserOrm.is_admin.is_(True)).order_by(UserOrm.id)
        result = await session.execute(stmt)
        return result.scalars().all()

    @classmethod
    async def get_or_create(cls, session: AsyncSession, create_schema: UserCreateS) -> UserOrm:
        user = await cls.get_by_tg_id(session=session, tg_id=create_schema.tg_id)
        if user is not None:
            return user
        stmt = insert(UserOrm).values(**create_schema.model_dump()).returning(UserOrm)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @classmethod
    async def get_by_username(cls, session: AsyncSession, username: str) -> UserOrm | None:
        scalar_result: ScalarResult[UserOrm] = await cls._get_by_fields(session=session, username=username)
        return scalar_result.one_or_none()
