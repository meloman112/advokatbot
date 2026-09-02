from __future__ import annotations

import html
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.config import settings
from src.core.schemas import RequestUpdateS, UserUpdateS
from src.filters import IsAdmin
from src.handlers.user import commands_router
from src.notify import request_card, status_label
from src.repository.request import RequestRepository
from src.repository.user import UserRepository
from src.states import AdminForm
from src.utils.enum import RequestStatusEnum
from src.utils.texts import load_json_text
from src.utils.tg import edit_text

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from sqlalchemy.ext.asyncio import AsyncSession


router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 5


def admin_menu_kb(is_superadmin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📥 Новые обращения", callback_data="a:reqs:new:0")],
        [InlineKeyboardButton(text="📋 Все обращения", callback_data="a:reqs:all:0")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="a:users:0")],
    ]
    if is_superadmin:
        rows.append([InlineKeyboardButton(text="🛡 Админы", callback_data="a:admins")])
    rows.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pager(callback_prefix: str, page: int, total: int) -> list[InlineKeyboardButton]:
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"{callback_prefix}:{page - 1}"))
    if (page + 1) * PAGE_SIZE < total:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"{callback_prefix}:{page + 1}"))
    return buttons


async def render_admin_menu(callback_or_message: Message | CallbackQuery, tg_id: int) -> None:
    kb = admin_menu_kb(is_superadmin=tg_id == settings.bot.superadmin_id)
    text = "🛠 Админ-панель"
    if isinstance(callback_or_message, CallbackQuery):
        if isinstance(callback_or_message.message, Message):
            await edit_text(callback_or_message.message, text, reply_markup=kb)
        return
    await callback_or_message.answer(text, reply_markup=kb)


@commands_router.message(Command("admin"), IsAdmin())
async def command_admin(message: Message, state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    await render_admin_menu(message, tg_id=message.from_user.id)


@router.callback_query(F.data == "a:menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await render_admin_menu(callback, tg_id=callback.from_user.id)
    await callback.answer()


@router.callback_query(F.data.startswith("a:reqs:"))
async def admin_requests(callback: CallbackQuery, session: AsyncSession) -> None:
    _, _, mode, raw_page = (callback.data or "").split(":")
    page = int(raw_page)
    only_new = mode == "new"
    total = await RequestRepository.count(session=session, only_new=only_new)
    requests = await RequestRepository.get_page(
        session=session,
        offset=page * PAGE_SIZE,
        limit=PAGE_SIZE,
        only_new=only_new,
    )
    rows = [
        [
            InlineKeyboardButton(
                text=f"#{request.id} {request.name[:20]} — {status_label(request)}",
                callback_data=f"a:req:{request.id}",
            )
        ]
        for request in requests
    ]
    nav = pager(f"a:reqs:{mode}", page=page, total=total)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="a:menu")])
    title = "📥 Новые обращения" if only_new else "📋 Все обращения"
    body = f"{title} ({total})" if requests else f"{title}: пусто"
    if isinstance(callback.message, Message):
        await edit_text(callback.message, body, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data.startswith("a:req:"))
async def admin_request_detail(callback: CallbackQuery, session: AsyncSession) -> None:
    request_id = int((callback.data or "").split(":")[2])
    request = await RequestRepository.get_one(session=session, id_=request_id)
    if request is None:
        await callback.answer("Обращение не найдено", show_alert=True)
        return
    rows = [
        [InlineKeyboardButton(text="✉️ Ответить", callback_data=f"a:ans:{request.id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="a:reqs:all:0")],
    ]
    if isinstance(callback.message, Message):
        await edit_text(
            callback.message, request_card(request), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )
    await callback.answer()


@router.callback_query(F.data.startswith("a:ans:"))
async def admin_answer_start(callback: CallbackQuery, state: FSMContext) -> None:
    request_id = int((callback.data or "").split(":")[2])
    await state.set_state(AdminForm.answer)
    await state.update_data(request_id=request_id)
    if isinstance(callback.message, Message):
        await callback.message.answer(f"Напишите ответ на обращение №{request_id}\n\nОтмена: /cancel")
    await callback.answer()


@router.message(AdminForm.answer)
async def admin_answer_send(message: Message, bot: Bot, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None:
        return
    answer = (message.text or "").strip()
    if not answer:
        await message.answer("Ответ должен быть текстом.")
        return
    request_id = int((await state.get_data())["request_id"])
    await state.clear()
    request = await RequestRepository.get_one(session=session, id_=request_id)
    if request is None:
        await message.answer("Обращение не найдено.")
        return
    user_texts: dict[str, Any] = await load_json_text(request.user.lang)
    try:
        await bot.send_message(
            chat_id=request.user.tg_id,
            text=user_texts["answer_received"].format(request_id=request_id, answer=html.escape(answer)),
        )
    except TelegramForbiddenError:
        await message.answer("Клиент заблокировал бота — ответ не доставлен. Свяжитесь по телефону из карточки.")
        return
    await RequestRepository.update_by_id(
        session=session,
        id_=request_id,
        update_schema=RequestUpdateS(
            status=RequestStatusEnum.ANSWERED,
            answer=answer,
            answered_by=message.from_user.id,
        ),
    )
    await message.answer(f"Ответ отправлен по обращению №{request_id}.")
    await render_admin_menu(message, tg_id=message.from_user.id)


@router.callback_query(F.data.startswith("a:users:"))
async def admin_users(callback: CallbackQuery, session: AsyncSession) -> None:
    page = int((callback.data or "").split(":")[2])
    total = await UserRepository.count(session=session)
    users = await UserRepository.get_page(session=session, offset=page * PAGE_SIZE, limit=PAGE_SIZE)
    lines = [
        f"👤 {html.escape(user.first_name)} "
        f"{('@' + user.username) if user.username else user.tg_id} — {user.lang}"
        f"{' 🛡' if user.is_admin else ''}"
        for user in users
    ]
    rows = []
    nav = pager("a:users", page=page, total=total)
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="a:menu")])
    body = "👥 Пользователи ({}):\n\n{}".format(total, "\n".join(lines)) if lines else "👥 Пользователей нет"
    if isinstance(callback.message, Message):
        await edit_text(callback.message, body, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data == "a:admins")
async def admin_admins(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user.id != settings.bot.superadmin_id:
        await callback.answer("Только суперадмин", show_alert=True)
        return
    admins = await UserRepository.get_admins(session=session)
    rows = [
        [
            InlineKeyboardButton(
                text=f"➖ {admin.first_name} {('@' + admin.username) if admin.username else admin.tg_id}",
                callback_data=f"a:admin_del:{admin.tg_id}",
            )
        ]
        for admin in admins
    ]
    rows.append([InlineKeyboardButton(text="➕ Добавить админа", callback_data="a:admin_add")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="a:menu")])
    body = "🛡 Админы (нажмите, чтобы снять права):" if admins else "🛡 Админов нет"
    if isinstance(callback.message, Message):
        await edit_text(callback.message, body, reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await callback.answer()


@router.callback_query(F.data == "a:admin_add")
async def admin_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.from_user.id != settings.bot.superadmin_id:
        await callback.answer("Только суперадмин", show_alert=True)
        return
    await state.set_state(AdminForm.new_admin)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            "Отправьте Telegram ID или @username пользователя. Он должен хотя бы раз запустить бота.\n\nОтмена: /cancel"
        )
    await callback.answer()


@router.message(AdminForm.new_admin)
async def admin_add_finish(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if message.from_user is None or message.from_user.id != settings.bot.superadmin_id:
        return
    raw = (message.text or "").strip().lstrip("@")
    user = (
        await UserRepository.get_by_tg_id(session=session, tg_id=int(raw))
        if raw.isdigit()
        else await UserRepository.get_by_username(session=session, username=raw)
    )
    if user is None:
        await message.answer("Пользователь не найден. Он должен сначала написать боту /start.")
        return
    await state.clear()
    await UserRepository.update_by_tg_id(session=session, tg_id=user.tg_id, update_schema=UserUpdateS(is_admin=True))
    await message.answer(f"{user.first_name} теперь админ.")
    await render_admin_menu(message, tg_id=message.from_user.id)


@router.callback_query(F.data.startswith("a:admin_del:"))
async def admin_del(callback: CallbackQuery, session: AsyncSession) -> None:
    if callback.from_user.id != settings.bot.superadmin_id:
        await callback.answer("Только суперадмин", show_alert=True)
        return
    tg_id = int((callback.data or "").split(":")[2])
    await UserRepository.update_by_tg_id(session=session, tg_id=tg_id, update_schema=UserUpdateS(is_admin=False))
    await admin_admins(callback, session=session)
