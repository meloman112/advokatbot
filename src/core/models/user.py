from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.models.base import BaseOrm
from src.core.models.mixins import TimestampMixin
from src.utils.enum import LanguageEnum


class UserOrm(BaseOrm, TimestampMixin):
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String(30))
    username: Mapped[str | None] = mapped_column(String(50), unique=True)
    last_name: Mapped[str | None] = mapped_column(String(30))

    lang: Mapped[str] = mapped_column(String(2), default=LanguageEnum.RU)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
