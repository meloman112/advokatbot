from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, insert, select

from src.core.models import RequestOrm
from src.core.schemas import RequestCreateS, RequestUpdateS
from src.repository.base import BaseRepository
from src.utils.enum import RequestStatusEnum

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession


class RequestRepository(BaseRepository[RequestOrm, RequestCreateS, RequestUpdateS]):
    model_class: type[RequestOrm] = RequestOrm

    @classmethod
    async def create_and_get(cls, session: AsyncSession, create_schema: RequestCreateS) -> RequestOrm:
        stmt = insert(RequestOrm).values(**create_schema.model_dump()).returning(RequestOrm)
        result = await session.execute(stmt)
        await session.commit()
        return result.scalar_one()

    @classmethod
    async def get_page(
        cls, session: AsyncSession, offset: int, limit: int, only_new: bool = False
    ) -> Sequence[RequestOrm]:
        stmt = select(RequestOrm).order_by(RequestOrm.id.desc()).offset(offset).limit(limit)
        if only_new:
            stmt = stmt.where(RequestOrm.status == RequestStatusEnum.NEW)
        result = await session.execute(stmt)
        return result.unique().scalars().all()

    @classmethod
    async def count(cls, session: AsyncSession, only_new: bool = False) -> int:
        stmt = select(func.count()).select_from(RequestOrm)
        if only_new:
            stmt = stmt.where(RequestOrm.status == RequestStatusEnum.NEW)
        return (await session.execute(stmt)).scalar_one()

    @classmethod
    async def get_by_user_id(cls, session: AsyncSession, user_id: int, limit: int = 10) -> Sequence[RequestOrm]:
        stmt = select(RequestOrm).where(RequestOrm.user_id == user_id).order_by(RequestOrm.id.desc()).limit(limit)
        result = await session.execute(stmt)
        return result.unique().scalars().all()

    @classmethod
    async def get_one(cls, session: AsyncSession, id_: int) -> RequestOrm | None:
        stmt = select(RequestOrm).where(RequestOrm.id == id_)
        result = await session.execute(stmt)
        return result.unique().scalar_one_or_none()
