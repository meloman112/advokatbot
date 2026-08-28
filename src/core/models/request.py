from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.models.base import BaseOrm
from src.core.models.mixins import TimestampMixin
from src.core.models.user import UserOrm
from src.utils.enum import RequestStatusEnum


class RequestOrm(BaseOrm, TimestampMixin):
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(32))
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default=RequestStatusEnum.NEW)
    answer: Mapped[str | None] = mapped_column(Text)
    answered_by: Mapped[int | None] = mapped_column(BigInteger)

    user: Mapped[UserOrm] = relationship(lazy="joined")
