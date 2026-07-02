"""Главное меню, профиль, привязка TikTok."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from .. import database as db
from .. import keyboards as kb
from ..config import config
from ..services import tiktok
from ..tariffs import get_tariff

router = Router()

WELCOME = (
    "👋 <b>TikTok Uploader Bot</b>\n\n"
    "Загружаю ваши вертикальные видео (Reels/Shorts/клипы) прямо в TikTok "
    "в обход региональных ограничений РФ — трафик идёт через сервер вне России.\n\n"
    "Как начать:\n"
    "1️⃣ Привяжите аккаунт TikTok\n"
    "2️⃣ Выберите тариф\n"
    "3️⃣ Пришлите ссылку на видео или сам файл\n\n"
    "Выберите действие 👇"
)


@router.message(CommandStart())
async def start(message: Message) -> None:
    await db.get_or_create_user(message.from_user.id, message.from_user.username)
    await message.answer(WELCOME, reply_markup=kb.main_menu())


@router.callback_query(F.data == "menu")
async def show_menu(cb: CallbackQuery) -> None:
    await cb.message.edit_text(WELCOME, reply_markup=kb.main_menu())
    await cb.answer()


@router.callback_query(F.data == "profile")
async def profile(cb: CallbackQuery) -> None:
    user = await db.get_or_create_user(cb.from_user.id, cb.from_user.username)
    t = get_tariff(user["tariff"])
    used = await db.count_today_uploads(cb.from_user.id)
    linked = "✅ привязан" if user["tiktok_token"] else "❌ не привязан"
    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"Тариф: <b>{t.title}</b> ({t.daily_limit} видео/сутки)\n"
        f"Использовано сегодня: <b>{used}/{t.daily_limit}</b>\n"
        f"Подписка до: <b>{user['tariff_until'] or '—'}</b>\n"
        f"TikTok: {linked}"
    )
    await cb.message.edit_text(text, reply_markup=kb.back_kb())
    await cb.answer()


@router.callback_query(F.data == "link_tiktok")
async def link_tiktok(cb: CallbackQuery) -> None:
    if not config.tiktok_client_key or not config.tiktok_redirect_uri:
        await cb.message.edit_text(
            "⚠️ Привязка TikTok ещё не настроена администратором "
            "(нужны TIKTOK_CLIENT_KEY и TIKTOK_REDIRECT_URI).",
            reply_markup=kb.back_kb(),
        )
        await cb.answer()
        return
    url = tiktok.build_oauth_url(state=str(cb.from_user.id))
    await cb.message.edit_text(
        "🔗 Нажмите кнопку ниже и разрешите боту публиковать видео в вашем TikTok.\n"
        "После подтверждения вернитесь в бот.",
        reply_markup=kb.link_tiktok_kb(url),
    )
    await cb.answer()
