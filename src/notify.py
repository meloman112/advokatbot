from __future__ import annotations

import html
import logging
from typing import TYPE_CHECKING

from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.config import settings
from src.repository.user import UserRepository
from src.utils.enum import RequestStatusEnum

if TYPE_CHECKING:
    from aiogram import Bot
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.models import RequestOrm

log = logging.getLogger(__name__)


def status_label(request: RequestOrm) -> str:
    return "новое" if request.status == RequestStatusEnum.NEW else "отвечено"


def request_card(request: RequestOrm) -> str:
    user = request.user
    contact = f"@{user.username}" if user.username else f'<a href="tg://user?id={user.tg_id}">{user.tg_id}</a>'
    card = (
        f"Обращение №{request.id} — {status_label(request)}\n"
        f"🕒 {request.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"👤 {html.escape(request.name)}\n"
        f"📱 {html.escape(request.phone)}\n"
        f"🌐 {user.lang}\n"
        f"🔗 {contact}\n\n"
        f"📄 {html.escape(request.text)}"
    )
    if request.answer:
        card += f"\n\n💬 Ответ:\n{html.escape(request.answer)}"
    return card


async def admin_ids(session: AsyncSession) -> list[int]:
    admins = await UserRepository.get_admins(session=session)
    ids = [settings.bot.superadmin_id] + [admin.tg_id for admin in admins]
    return list(dict.fromkeys(ids))


async def notify_admins(bot: Bot, session: AsyncSession, request: RequestOrm) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✉️ Ответить", callback_data=f"a:ans:{request.id}")]]
    )
    text = f"🆕 {request_card(request)}"
    delivered = 0
    for tg_id in await admin_ids(session=session):
        try:
            await bot.send_message(chat_id=tg_id, text=text, reply_markup=kb)
        except TelegramForbiddenError:
            log.warning("Админ %s заблокировал бота, обращение №%s не доставлено", tg_id, request.id)
            continue
        delivered += 1
    if delivered == 0:
        log.error("Обращение №%s не доставлено ни одному админу", request.id)
