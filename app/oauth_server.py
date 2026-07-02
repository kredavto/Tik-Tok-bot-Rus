"""Небольшой HTTP-сервер для OAuth-callback TikTok.

TikTok после привязки редиректит пользователя на TIKTOK_REDIRECT_URI?code=...&state=<user_id>.
Здесь мы меняем code на access_token и сохраняем его пользователю.
Запускается вместе с ботом (см. main.py). Должен быть доступен по HTTPS
(например, через reverse-proxy/домен), совпадающему с TIKTOK_REDIRECT_URI.
"""
from __future__ import annotations

from aiohttp import web

from . import database as db
from .services import tiktok


async def _callback(request: web.Request) -> web.Response:
    code = request.query.get("code")
    state = request.query.get("state")  # тут лежит telegram user_id
    if not code or not state:
        return web.Response(text="Missing code/state", status=400)
    try:
        token = await tiktok.exchange_code(code)
        await db.set_tiktok_token(
            int(state),
            token["access_token"],
            token.get("open_id", ""),
        )
    except Exception as exc:  # noqa: BLE001
        return web.Response(text=f"Ошибка привязки: {exc}", status=500)
    return web.Response(
        text="✅ Аккаунт TikTok привязан! Вернитесь в Telegram-бот.",
        content_type="text/plain",
    )


def build_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/tiktok/callback", _callback)
    app.router.add_get("/health", lambda r: web.Response(text="ok"))
    return app


async def start_oauth_server(host: str = "0.0.0.0", port: int = 8080) -> web.AppRunner:
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner
