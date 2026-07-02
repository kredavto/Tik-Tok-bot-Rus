"""Оплата тарифов через Telegram Payments или Telegram Stars (XTR)."""
from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from .. import database as db
from .. import keyboards as kb
from ..config import config
from ..tariffs import TARIFFS, get_tariff

router = Router()


@router.callback_query(F.data == "tariffs")
async def show_tariffs(cb: CallbackQuery) -> None:
    lines = ["💎 <b>Тарифы</b> (списание за 30 дней подписки):\n"]
    for t in TARIFFS.values():
        lines.append(f"• <b>{t.title}</b> — ${t.price_usd:g} · {t.description}")
    lines.append("\nВыберите тариф для оплаты 👇")
    await cb.message.edit_text("\n".join(lines), reply_markup=kb.tariffs_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy(cb: CallbackQuery) -> None:
    code = cb.data.split(":", 1)[1]
    tariff = get_tariff(code)

    if config.use_stars:
        prices = [LabeledPrice(label=f"Тариф {tariff.title}", amount=tariff.price_stars)]
        await cb.message.answer_invoice(
            title=f"Тариф {tariff.title}",
            description=f"{tariff.description}. Подписка на 30 дней.",
            payload=f"tariff:{code}",
            currency="XTR",
            prices=prices,
            provider_token="",  # Stars не требуют provider_token
        )
    else:
        prices = [LabeledPrice(label=f"Тариф {tariff.title}", amount=tariff.price_cents)]
        await cb.message.answer_invoice(
            title=f"Тариф {tariff.title}",
            description=f"{tariff.description}. Подписка на 30 дней.",
            payload=f"tariff:{code}",
            provider_token=config.payment_provider_token,
            currency=config.currency,
            prices=prices,
        )
    await cb.answer()


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery) -> None:
    await q.answer(ok=True)


@router.message(F.successful_payment)
async def on_paid(message: Message) -> None:
    sp = message.successful_payment
    code = sp.invoice_payload.split(":", 1)[1]
    tariff = get_tariff(code)
    until = (datetime.utcnow() + timedelta(days=30)).date().isoformat()

    await db.set_tariff(message.from_user.id, code, until)
    await db.add_payment(
        message.from_user.id, code,
        tariff.price_usd, sp.currency,
        sp.provider_payment_charge_id or sp.telegram_payment_charge_id,
    )
    await message.answer(
        f"✅ Оплата получена! Тариф <b>{tariff.title}</b> активен до <b>{until}</b>.\n"
        f"Теперь доступно {tariff.daily_limit} видео в сутки.",
        reply_markup=kb.main_menu(),
    )
