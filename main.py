"""Точка входа: запуск Telegram-бота (long polling) + OAuth-сервер TikTok."""
from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode

from app import database as db
from app.config import config
from app.handlers import get_router
from app.oauth_server import start_web_server

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")


async def main() -> None:
    if not config.bot_token:
        raise SystemExit("BOT_TOKEN не задан. Заполните .env (см. .env.example).")

    await db.init_db()

    # В РФ прямой доступ к api.telegram.org часто заблокирован (DPI). Если задан
    # TELEGRAM_PROXY (сервер вне РФ), весь трафик к Telegram идёт через него.
    session = None
    if config.telegram_proxy:
        session = AiohttpSession(proxy=config.telegram_proxy)
        log.info("Telegram через прокси: %s", config.telegram_proxy)

    bot = Bot(
        token=config.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(get_router())

    tiktok_ready = bool(config.tiktok_client_key and config.tiktok_redirect_uri)
    runner = None
    # Веб-сервер нужен для OAuth TikTok и/или колбэка оплаты Robokassa.
    if tiktok_ready or config.use_robokassa:
        runner = await start_web_server(bot=bot, port=config.web_port)
        log.info("Веб-сервер запущен на порту %s (TikTok=%s, Robokassa=%s)",
                 config.web_port, tiktok_ready, config.use_robokassa)
    if not tiktok_ready:
        log.warning("TikTok OAuth не настроен — привязка аккаунтов недоступна.")
    if config.use_robokassa:
        log.info("Оплата: Robokassa (тест=%s)", config.robokassa_test)

    try:
        log.info("Бот запущен.")
        await dp.start_polling(bot)
    finally:
        if runner:
            await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
