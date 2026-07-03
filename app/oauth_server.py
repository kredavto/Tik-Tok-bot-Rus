"""HTTP-сервер бота: OAuth-callback TikTok + колбэк оплаты Robokassa.

Запускается вместе с ботом (см. main.py), если настроен TikTok OAuth и/или
Robokassa. Должен быть публично доступен по адресу PUBLIC_BASE_URL:
  - TikTok:    {PUBLIC_BASE_URL}/tiktok/callback   (= TIKTOK_REDIRECT_URI)
  - Robokassa: {PUBLIC_BASE_URL}/robokassa/result  (ResultURL в кабинете)
               {PUBLIC_BASE_URL}/robokassa/success (SuccessURL)
               {PUBLIC_BASE_URL}/robokassa/fail     (FailURL)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiohttp import web

from . import database as db
from .config import config
from .keyboards import main_menu
from .services import robokassa, tiktok

log = logging.getLogger("web")


async def _tiktok_callback(request: web.Request) -> web.Response:
    code = request.query.get("code")
    state = request.query.get("state")  # telegram user_id
    if not code or not state:
        return web.Response(text="Missing code/state", status=400)
    try:
        token = await tiktok.exchange_code(code)
        await db.set_tiktok_token(int(state), token["access_token"],
                                 token.get("open_id", ""))
    except Exception as exc:  # noqa: BLE001
        return web.Response(text=f"Ошибка привязки: {exc}", status=500)
    return web.Response(text="✅ Аккаунт TikTok привязан! Вернитесь в Telegram-бот.",
                        content_type="text/plain")


async def _robokassa_result(request: web.Request) -> web.Response:
    """ResultURL: серверное уведомление об успешной оплате."""
    data = request.query if request.method == "GET" else await request.post()
    out_sum = data.get("OutSum")
    inv_id = data.get("InvId")
    signature = data.get("SignatureValue")
    shp = {k: v for k, v in data.items() if k.startswith("Shp_")}

    if not (out_sum and inv_id and signature) or \
            not robokassa.check_result_signature(out_sum, inv_id, signature, shp):
        return web.Response(text="bad sign", status=400)

    invoice = await db.get_invoice(int(inv_id))
    if invoice is None:
        return web.Response(text="unknown invoice", status=400)

    if invoice["status"] != "paid":
        until = (datetime.utcnow() + timedelta(days=30)).date().isoformat()
        await db.set_tariff(invoice["user_id"], invoice["tariff"], until)
        await db.mark_invoice_paid(int(inv_id))
        await db.add_payment(invoice["user_id"], invoice["tariff"],
                             invoice["amount"], "RUB", f"robokassa:{inv_id}")
        bot: Bot | None = request.app.get("bot")
        if bot is not None:
            try:
                await bot.send_message(
                    invoice["user_id"],
                    f"✅ Оплата получена! Тариф активен до <b>{until}</b>.",
                    reply_markup=main_menu(),
                )
            except Exception:  # noqa: BLE001
                log.exception("Не удалось уведомить пользователя об оплате")

    # Robokassa ожидает ответ строго в виде OK{InvId}
    return web.Response(text=f"OK{inv_id}")


async def _robokassa_success(request: web.Request) -> web.Response:
    return web.Response(text="✅ Оплата прошла успешно! Вернитесь в Telegram-бот.",
                        content_type="text/plain")


async def _robokassa_fail(request: web.Request) -> web.Response:
    return web.Response(text="❌ Оплата не завершена. Можно попробовать снова в боте.",
                        content_type="text/plain")


def build_app(bot: Bot | None = None) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    app.router.add_get("/tiktok/callback", _tiktok_callback)
    app.router.add_route("*", "/robokassa/result", _robokassa_result)
    app.router.add_get("/robokassa/success", _robokassa_success)
    app.router.add_get("/robokassa/fail", _robokassa_fail)
    return app


async def start_web_server(bot: Bot | None = None, host: str = "0.0.0.0",
                           port: int = 8080) -> web.AppRunner:
    runner = web.AppRunner(build_app(bot))
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner


# Обратная совместимость со старым именем
start_oauth_server = start_web_server
