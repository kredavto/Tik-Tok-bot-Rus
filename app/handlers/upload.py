"""Приём видео/ссылки и загрузка в TikTok с учётом суточной квоты."""
from __future__ import annotations

import os
import re

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from .. import database as db
from .. import keyboards as kb
from ..services import downloader, tiktok
from ..tariffs import get_tariff

router = Router()

URL_RE = re.compile(r"https?://\S+")


@router.callback_query(F.data == "upload")
async def upload_hint(cb: CallbackQuery) -> None:
    await cb.message.edit_text(
        "📎 Пришлите <b>ссылку</b> на видео (Reels, Shorts, TikTok и т.п.) "
        "или загрузите видеофайл прямо сюда.",
        reply_markup=kb.back_kb(),
    )
    await cb.answer()


async def _check_quota(user_id: int) -> tuple[bool, str]:
    user = await db.get_or_create_user(user_id, None)
    tariff = get_tariff(user["tariff"])
    used = await db.count_today_uploads(user_id)
    if used >= tariff.daily_limit:
        return False, (
            f"🚫 Лимит тарифа <b>{tariff.title}</b> исчерпан "
            f"({used}/{tariff.daily_limit} за сутки).\n"
            "Оформите тариф выше в разделе 💎 Тарифы."
        )
    if not user["tiktok_token"]:
        return False, "🔗 Сначала привяжите аккаунт TikTok (кнопка в меню)."
    return True, user["tiktok_token"]


async def _process(message: Message, file_path: str, source: str) -> None:
    ok, payload = await _check_quota(message.from_user.id)
    if not ok:
        await message.answer(payload, reply_markup=kb.main_menu())
        if os.path.exists(file_path):
            os.remove(file_path)
        return

    access_token = payload
    upload_id = await db.add_upload(message.from_user.id, source, "pending")
    status = await message.answer("⏳ Загружаю видео в TikTok через сервер вне РФ…")
    try:
        result = await tiktok.upload_video(access_token, file_path, caption="")
        await db.set_upload_status(upload_id, "done")
        if result.get("mode") == "direct":
            done_text = "✅ Готово! Видео опубликовано в TikTok."
        else:
            done_text = (
                "✅ Готово! Видео загружено в <b>Черновики</b> TikTok.\n"
                "Откройте приложение TikTok → Профиль → Черновики, чтобы "
                "опубликовать его."
            )
        await status.edit_text(
            f"{done_text}\npublish_id: <code>{result.get('publish_id')}</code>",
            reply_markup=kb.main_menu(),
        )
    except tiktok.TikTokError as exc:
        await db.set_upload_status(upload_id, "failed")
        await status.edit_text(f"❌ Ошибка загрузки в TikTok: {exc}",
                               reply_markup=kb.main_menu())
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


@router.message(F.video)
async def on_video_file(message: Message) -> None:
    ok, payload = await _check_quota(message.from_user.id)
    if not ok:
        await message.answer(payload, reply_markup=kb.main_menu())
        return
    os.makedirs(downloader.DOWNLOAD_DIR, exist_ok=True)
    path = os.path.join(downloader.DOWNLOAD_DIR, f"{message.video.file_id}.mp4")
    await message.bot.download(message.video, destination=path)
    await _process(message, path, source="telegram_upload")


@router.message(F.text.regexp(URL_RE.pattern))
async def on_url(message: Message) -> None:
    url = URL_RE.search(message.text).group(0)
    ok, payload = await _check_quota(message.from_user.id)
    if not ok:
        await message.answer(payload, reply_markup=kb.main_menu())
        return
    note = await message.answer("⬇️ Скачиваю исходное видео…")
    try:
        path = await downloader.download_video(url)
    except downloader.DownloadError as exc:
        await note.edit_text(f"❌ {exc}", reply_markup=kb.main_menu())
        return
    await note.delete()
    await _process(message, path, source=url)
