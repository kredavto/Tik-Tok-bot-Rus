"""Админ-команды."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from .. import database as db
from ..config import config

router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


@router.message(Command("stats"))
async def stats(message: Message) -> None:
    if not _is_admin(message.from_user.id):
        return
    s = await db.stats()
    await message.answer(
        "📊 <b>Статистика</b>\n"
        f"Пользователей: {s['users']}\n"
        f"Успешных загрузок: {s['uploads']}\n"
        f"Выручка (в $ по прайсу): {s['revenue']:.2f}"
    )


@router.message(Command("grant"))
async def grant(message: Message) -> None:
    """/grant <user_id> <tariff> — вручную выдать тариф (админ)."""
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) != 3:
        await message.answer("Использование: /grant <user_id> <free|pro|business>")
        return
    from datetime import datetime, timedelta
    until = (datetime.utcnow() + timedelta(days=30)).date().isoformat()
    await db.set_tariff(int(parts[1]), parts[2], until)
    await message.answer(f"✅ Пользователю {parts[1]} выдан тариф {parts[2]} до {until}.")
