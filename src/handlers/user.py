from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING, Any

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from src.config import settings
from src.core.schemas import RequestCreateS, UserCreateS, UserUpdateS
from src.keyboards import back_kb, language_kb, menu_kb, phone_kb
from src.repository.request import RequestRepository
from src.repository.user import UserRepository
from src.states import RequestForm
from src.utils.access import is_admin
from src.utils.enum import LanguageEnum, RequestStatusEnum
from src.utils.texts import load_json_text
from src.utils.tg import edit_text

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.fsm.context import FSMContext
    from sqlalchemy.ext.asyncio import AsyncSession

    from src.core.models import RequestOrm, UserOrm

router = Router()
# Команды-выходы: подключаются первыми, чтобы не быть съеденными хендлерами FSM-состояний.
commands_router = Router()

PHONE_RE = re.compile(r"^\+?\d{9,15}$")


async def show_menu(target: Message | CallbackQuery, session: AsyncSession, texts: dict[str, Any]) -> None:
    user = target.from_user
    if user is None:
        return
    text: str = texts["menu"]
    kb = menu_kb(texts, is_admin=await is_admin(session=session, tg_id=user.id))
    if isinstance(target, CallbackQuery):
        if isinstance(target.message, Message):
            await edit_text(target.message, text, reply_markup=kb)
        return
    await target.answer(text, reply_markup=kb)


@commands_router.message(CommandStart())
async def command_start(message: Message, session: AsyncSession, texts: dict[str, Any], state: FSMContext) -> None:
    if message.from_user is None:
        return
    await state.clear()
    known = await UserRepository.get_by_tg_id(session=session, tg_id=message.from_user.id)
    await UserRepository.get_or_create(
        session=session,
        create_schema=UserCreateS(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        ),
    )
    if known is None:
        await message.answer(texts["choose_language"], reply_markup=language_kb())
        return
    await show_menu(message, session=session, texts=texts)


@commands_router.message(Command("cancel"))
async def command_cancel(message: Message, session: AsyncSession, texts: dict[str, Any], state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts["cancelled"], reply_markup=ReplyKeyboardRemove())
    await show_menu(message, session=session, texts=texts)


@router.callback_query(F.data == "lang:menu")
async def open_language(callback: CallbackQuery, texts: dict[str, Any]) -> None:
    if isinstance(callback.message, Message):
        await edit_text(callback.message, texts["choose_language"], reply_markup=language_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, session: AsyncSession) -> None:
    lang = callback.data.split(":", 1)[1] if callback.data else LanguageEnum.RU
    if lang not in tuple(LanguageEnum):
        await callback.answer()
        return
    await UserRepository.update_by_tg_id(
        session=session,
        tg_id=callback.from_user.id,
        update_schema=UserUpdateS(lang=lang),
    )
    texts = await load_json_text(lang)
    await callback.answer(texts["language_set"])
    await show_menu(callback, session=session, texts=texts)


@router.callback_query(F.data == "menu")
async def back_to_menu(
    callback: CallbackQuery, session: AsyncSession, texts: dict[str, Any], state: FSMContext
) -> None:
    await state.clear()
    await show_menu(callback, session=session, texts=texts)
    await callback.answer()


@router.callback_query(F.data == "req:new")
async def new_request(callback: CallbackQuery, texts: dict[str, Any], state: FSMContext) -> None:
    await state.set_state(RequestForm.name)
    if isinstance(callback.message, Message):
        await callback.message.answer(f"{texts['ask_name']}\n\n{texts['cancel_hint']}")
    await callback.answer()


@router.message(RequestForm.name)
async def form_name(message: Message, texts: dict[str, Any], state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not 2 <= len(name) <= 100:
        await message.answer(texts["invalid_name"])
        return
    await state.update_data(name=name)
    await state.set_state(RequestForm.phone)
    await message.answer(texts["ask_phone"], reply_markup=phone_kb(texts))


@router.message(RequestForm.phone)
async def form_phone(message: Message, texts: dict[str, Any], state: FSMContext) -> None:
    raw = message.contact.phone_number if message.contact else (message.text or "")
    phone = re.sub(r"[\s\-()]", "", raw)
    if not PHONE_RE.match(phone):
        await message.answer(texts["invalid_phone"])
        return
    await state.update_data(phone=phone)
    await state.set_state(RequestForm.text)
    await message.answer(texts["ask_text"], reply_markup=ReplyKeyboardRemove())


@router.message(RequestForm.text)
async def form_text(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    texts: dict[str, Any],
    lang: str,
    state: FSMContext,
) -> None:
    if message.from_user is None:
        return
    text = (message.text or "").strip()
    if not 10 <= len(text) <= 3000:
        await message.answer(texts["invalid_text"])
        return
    data = await state.get_data()
    await state.clear()

    user = await UserRepository.get_or_create(
        session=session,
        create_schema=UserCreateS(
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        ),
    )
    request = await RequestRepository.create_and_get(
        session=session,
        create_schema=RequestCreateS(user_id=user.id, name=data["name"], phone=data["phone"], text=text),
    )
    await post_to_channel(bot=bot, request=request, user=user, lang=lang)
    await message.answer(texts["request_sent"].format(request_id=request.id))
    await show_menu(message, session=session, texts=texts)


async def post_to_channel(bot: Bot, request: RequestOrm, user: UserOrm, lang: str) -> None:
    channel_texts = await load_json_text(LanguageEnum.RU)
    contact = f"@{user.username}" if user.username else f'<a href="tg://user?id={user.tg_id}">{user.tg_id}</a>'
    await bot.send_message(
        chat_id=settings.bot.channel_id,
        text=channel_texts["channel_post"].format(
            request_id=request.id,
            name=html.escape(request.name),
            phone=html.escape(request.phone),
            lang=lang,
            contact=contact,
            text=html.escape(request.text),
        ),
    )


@router.callback_query(F.data == "req:my")
async def my_requests(callback: CallbackQuery, session: AsyncSession, texts: dict[str, Any]) -> None:
    user = await UserRepository.get_by_tg_id(session=session, tg_id=callback.from_user.id)
    requests = await RequestRepository.get_by_user_id(session=session, user_id=user.id) if user else []
    if not requests:
        body = texts["my_requests_empty"]
    else:
        cards = [render_request(request, texts) for request in requests]
        body = "{}\n\n{}".format(texts["my_requests_title"], "\n\n".join(cards))
    if isinstance(callback.message, Message):
        await edit_text(callback.message, body, reply_markup=back_kb(texts))
    await callback.answer()


def render_request(request: RequestOrm, texts: dict[str, Any]) -> str:
    status = texts["status_new"] if request.status == RequestStatusEnum.NEW else texts["status_answered"]
    card: str = texts["request_card"].format(
        request_id=request.id,
        date=request.created_at.strftime("%d.%m.%Y"),
        status=status,
        text=html.escape(request.text),
    )
    if request.answer:
        card += texts["request_answer"].format(answer=html.escape(request.answer))
    return card
