"""Оплата тарифов через Telegram Payments или Telegram Stars (XTR)."""
from __future__ import annotations

from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)

from .. import database as db
from .. import keyboards as kb
from ..config import config
from ..services import robokassa
from ..tariffs import TARIFFS, get_tariff

router = Router()


def _rub(price_usd: float) -> float:
    return round(price_usd * config.robokassa_usd_rate, 2)


@router.callback_query(F.data == "tariffs")
async def show_tariffs(cb: CallbackQuery) -> None:
    lines = ["💎 <b>Тарифы</b> (списание за 30 дней подписки):\n"]
    for t in TARIFFS.values():
        if config.use_robokassa:
            lines.append(f"• <b>{t.title}</b> — {_rub(t.price_usd):g}₽ · {t.description}")
        else:
            lines.append(f"• <b>{t.title}</b> — ${t.price_usd:g} · {t.description}")
    lines.append("\nВыберите тариф для оплаты 👇")
    await cb.message.edit_text("\n".join(lines), reply_markup=kb.tariffs_menu())
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy(cb: CallbackQuery) -> None:
    code = cb.data.split(":", 1)[1]
    tariff = get_tariff(code)

    # 1) Robokassa (приоритетно, если настроена)
    if config.use_robokassa:
        amount_rub = _rub(tariff.price_usd)
        inv_id = await db.create_invoice(cb.from_user.id, code, amount_rub)
        url = robokassa.build_payment_url(
            inv_id, amount_rub, f"Тариф {tariff.title}", cb.from_user.id, code,
        )
        markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"💳 Оплатить {amount_rub:g}₽", url=url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="tariffs")],
        ])
        await cb.message.edit_text(
            f"Тариф <b>{tariff.title}</b> — {tariff.description}.\n"
            f"К оплате: <b>{amount_rub:g}₽</b> (подписка на 30 дней).\n\n"
            "Нажмите кнопку ниже, оплатите на странице Robokassa — тариф "
            "активируется автоматически после подтверждения платежа.",
            reply_markup=markup,
        )
        await cb.answer()
        return

    # 2) Telegram Payments / Stars
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
