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
    # Режим загрузки: "draft" (в черновики, scope video.upload) или
    # "direct" (прямая публикация, scope video.publish, требует аудит).
    tiktok_upload_mode: str = os.getenv("TIKTOK_UPLOAD_MODE", "draft").lower()
    # Robokassa
    robokassa_login: str = os.getenv("ROBOKASSA_LOGIN", "")
    robokassa_password1: str = os.getenv("ROBOKASSA_PASSWORD1", "")
    robokassa_password2: str = os.getenv("ROBOKASSA_PASSWORD2", "")
    robokassa_test: bool = os.getenv("ROBOKASSA_TEST", "0") == "1"
    # Курс пересчёта $ -> ₽ (тарифы заданы в долларах, Robokassa берёт рубли)
    robokassa_usd_rate: float = float(os.getenv("ROBOKASSA_USD_RATE", "100"))
    # Публичный адрес веб-сервера (для ResultURL Robokassa и OAuth TikTok),
    # напр. http://5.129.234.72:8080
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "")
    web_port: int = int(os.getenv("PORT", "8080"))
    database_path: str = os.getenv("DATABASE_PATH", "bot.db")
    timezone: str = os.getenv("TIMEZONE", "Europe/Moscow")

    @property
    def use_robokassa(self) -> bool:
        """Robokassa настроена, если заданы логин и оба пароля."""
        return bool(self.robokassa_login and self.robokassa_password1
                    and self.robokassa_password2)

    @property
    def use_stars(self) -> bool:
        """Если ни Robokassa, ни провайдер Telegram Payments не заданы — Stars (XTR)."""
        return not self.payment_provider_token or self.currency.upper() == "XTR"


config = Config()
