"""Тарифные планы бота."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Tariff:
    code: str
    title: str
    daily_limit: int          # видео в сутки
    price_usd: float          # цена в долларах
    description: str

    @property
    def price_cents(self) -> int:
        """Цена в минимальных единицах валюты (для Telegram Payments)."""
        return round(self.price_usd * 100)

    @property
    def price_stars(self) -> int:
        """Приблизительный эквивалент в Telegram Stars (~$0.013 за звезду)."""
        return max(1, round(self.price_usd / 0.013))


TARIFFS: dict[str, Tariff] = {
    "free": Tariff(
        code="free",
        title="Free",
        daily_limit=1,
        price_usd=5.9,
        description="1 видео в сутки в TikTok",
    ),
    "pro": Tariff(
        code="pro",
        title="PRO",
        daily_limit=3,
        price_usd=9.9,
        description="3 видео в сутки в TikTok",
    ),
    "business": Tariff(
        code="business",
        title="Business",
        daily_limit=10,
        price_usd=19.9,
        description="10 видео в сутки в TikTok",
    ),
}

DEFAULT_TARIFF = "free"


def get_tariff(code: str) -> Tariff:
    return TARIFFS.get(code, TARIFFS[DEFAULT_TARIFF])
