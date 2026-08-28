from __future__ import annotations

from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.utils.enum import LanguageEnum


def language_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"lang:{LanguageEnum.RU}")],
            [InlineKeyboardButton(text="🇺🇿 Ўзбекча", callback_data=f"lang:{LanguageEnum.UZ}")],
        ]
    )


def menu_kb(texts: dict[str, Any], is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=texts["btn_new_request"], callback_data="req:new")],
        [InlineKeyboardButton(text=texts["btn_my_requests"], callback_data="req:my")],
        [InlineKeyboardButton(text=texts["btn_language"], callback_data="lang:menu")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=texts["btn_admin"], callback_data="a:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb(texts: dict[str, Any]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=texts["btn_back"], callback_data="menu")]])


def phone_kb(texts: dict[str, Any]) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=texts["btn_share_phone"], request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
