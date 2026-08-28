from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from datetime import datetime


class UserS(BaseModel):
    id: int
    tg_id: int
    first_name: str
    username: str | None
    last_name: str | None

    lang: str
    is_admin: bool
    is_active: bool

    created_at: datetime
    updated_at: datetime


class UserCreateS(BaseModel):
    tg_id: int
    first_name: str
    username: str | None
    last_name: str | None


class UserUpdateS(BaseModel):
    lang: str | None = None
    is_admin: bool | None = None
    is_active: bool | None = None
