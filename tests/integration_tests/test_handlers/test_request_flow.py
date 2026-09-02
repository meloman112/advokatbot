from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, Message, User

from src.config import settings
from src.core.schemas import RequestCreateS, UserCreateS
from src.handlers.admin import admin_answer_send
from src.handlers.user import form_name, form_phone, form_text, set_language
from src.repository.request import RequestRepository
from src.repository.user import UserRepository
from src.states import RequestForm
from src.utils.enum import LanguageEnum, RequestStatusEnum

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

TG_ID = 424242424
ADMIN_TG_ID = 515151515


def make_state() -> FSMContext:
    return FSMContext(storage=MemoryStorage(), key=StorageKey(bot_id=1, chat_id=TG_ID, user_id=TG_ID))


def make_message(text: str | None = None, tg_id: int = TG_ID) -> Any:
    message = Mock(spec=Message)
    message.from_user = User(id=tg_id, first_name="Anvar", last_name=None, username=None, is_bot=False)
    message.text = text
    message.contact = None
    message.answer = AsyncMock()
    return message


async def ensure_user(session: AsyncSession, tg_id: int = TG_ID) -> Any:
    return await UserRepository.get_or_create(
        session=session,
        create_schema=UserCreateS(tg_id=tg_id, first_name="Anvar", username=None, last_name=None),
    )


class TestRequestFlow:
    async def test_set_language_saves_choice(self, session: AsyncSession) -> None:
        await ensure_user(session)
        callback = Mock(spec=CallbackQuery)
        callback.data = f"lang:{LanguageEnum.UZ}"
        callback.from_user = User(id=TG_ID, first_name="Anvar", is_bot=False)
        callback.message = None
        callback.answer = AsyncMock()

        await set_language(callback=callback, session=session)

        user = await UserRepository.get_by_tg_id(session=session, tg_id=TG_ID)
        assert user is not None
        assert user.lang == LanguageEnum.UZ

    async def test_form_creates_request_and_notifies_admins(self, session: AsyncSession, json_text: Any) -> None:
        await ensure_user(session)
        state = make_state()
        bot = AsyncMock()

        await state.set_state(RequestForm.name)
        await form_name(message=make_message("Анвар Каримов"), texts=json_text, state=state)
        assert await state.get_state() == RequestForm.phone

        await form_phone(message=make_message("+998 90 123-45-67"), texts=json_text, state=state)
        assert await state.get_state() == RequestForm.text

        message = make_message("Нужна помощь по трудовому спору с работодателем")
        await form_text(message=message, bot=bot, session=session, texts=json_text, state=state)

        user = await UserRepository.get_by_tg_id(session=session, tg_id=TG_ID)
        assert user is not None
        requests = await RequestRepository.get_by_user_id(session=session, user_id=user.id)
        assert len(requests) == 1
        assert requests[0].phone == "+998901234567"
        assert requests[0].status == RequestStatusEnum.NEW
        bot.send_message.assert_awaited_once()
        assert bot.send_message.await_args.kwargs["chat_id"] == settings.bot.superadmin_id
        assert f"№{requests[0].id}" in bot.send_message.await_args.kwargs["text"]
        assert await state.get_state() is None

    @pytest.mark.parametrize("raw_phone", ["12345", "not a phone", "+99890123456789012"])
    async def test_form_rejects_bad_phone(self, raw_phone: str, json_text: Any) -> None:
        state = make_state()
        await state.set_state(RequestForm.phone)
        message = make_message(raw_phone)

        await form_phone(message=message, texts=json_text, state=state)

        assert await state.get_state() == RequestForm.phone
        message.answer.assert_awaited_with(json_text["invalid_phone"])


class TestAdminAnswer:
    async def test_answer_reaches_user_and_marks_request(self, session: AsyncSession, json_text: Any) -> None:
        user = await ensure_user(session)
        request = await RequestRepository.create_and_get(
            session=session,
            create_schema=RequestCreateS(
                user_id=user.id,
                name="Анвар",
                phone="+998901234567",
                text="Вопрос по договору аренды",
            ),
        )
        state = FSMContext(
            storage=MemoryStorage(),
            key=StorageKey(bot_id=1, chat_id=ADMIN_TG_ID, user_id=ADMIN_TG_ID),
        )
        await state.update_data(request_id=request.id)
        bot = AsyncMock()
        message = make_message("Приходите в офис в понедельник", tg_id=ADMIN_TG_ID)

        await admin_answer_send(message=message, bot=bot, session=session, state=state)

        answered = await RequestRepository.get_one(session=session, id_=request.id)
        assert answered is not None
        assert answered.status == RequestStatusEnum.ANSWERED
        assert answered.answer == "Приходите в офис в понедельник"
        assert answered.answered_by == ADMIN_TG_ID
        bot.send_message.assert_awaited_once()
        assert bot.send_message.await_args.kwargs["chat_id"] == user.tg_id
