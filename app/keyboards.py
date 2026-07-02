"""Inline-клавиатуры."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from .tariffs import TARIFFS


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="⬆️ Загрузить видео", callback_data="upload")
    kb.button(text="💎 Тарифы", callback_data="tariffs")
    kb.button(text="🔗 Привязать TikTok", callback_data="link_tiktok")
    kb.button(text="👤 Мой профиль", callback_data="profile")
    kb.adjust(1, 2, 1)
    return kb.as_markup()


def tariffs_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for t in TARIFFS.values():
        kb.button(
            text=f"{t.title} — ${t.price_usd:g} · {t.daily_limit}/сутки",
            callback_data=f"buy:{t.code}",
        )
    kb.button(text="⬅️ Назад", callback_data="menu")
    kb.adjust(1)
    return kb.as_markup()


def link_tiktok_kb(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Привязать аккаунт TikTok", url=url)],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu")],
    ])


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Меню", callback_data="menu")],
    ])
