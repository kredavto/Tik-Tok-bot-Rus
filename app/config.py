"""Загрузка конфигурации из переменных окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _int_list(raw: str | None) -> list[int]:
    if not raw:
        return []
    return [int(x) for x in raw.replace(" ", "").split(",") if x]


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=lambda: _int_list(os.getenv("ADMIN_IDS")))
    payment_provider_token: str = os.getenv("PAYMENT_PROVIDER_TOKEN", "")
    currency: str = os.getenv("CURRENCY", "USD")
    telegram_proxy: str = os.getenv("TELEGRAM_PROXY", "")
    tiktok_proxy: str = os.getenv("TIKTOK_PROXY", "")
    tiktok_client_key: str = os.getenv("TIKTOK_CLIENT_KEY", "")
    tiktok_client_secret: str = os.getenv("TIKTOK_CLIENT_SECRET", "")
    tiktok_redirect_uri: str = os.getenv("TIKTOK_REDIRECT_URI", "")
    database_path: str = os.getenv("DATABASE_PATH", "bot.db")
    timezone: str = os.getenv("TIMEZONE", "Europe/Moscow")

    @property
    def use_stars(self) -> bool:
        """Если провайдер платежей не задан — используем Telegram Stars (XTR)."""
        return not self.payment_provider_token or self.currency.upper() == "XTR"


config = Config()
