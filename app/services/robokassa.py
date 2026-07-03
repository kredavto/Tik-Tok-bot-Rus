"""Интеграция с Robokassa: платёжная ссылка и проверка подписи колбэка.

Схема оплаты:
  1. Пользователь жмёт «Оплатить» -> строим ссылку на страницу Robokassa
     с подписью (MerchantLogin:OutSum:InvId:Пароль#1[:Shp_...]).
  2. После оплаты Robokassa серверно вызывает ResultURL с параметрами
     OutSum, InvId, SignatureValue (MD5 с Паролем#2) — проверяем и активируем тариф.
  3. Пользователя редиректит на SuccessURL.

Docs: https://docs.robokassa.ru/
"""
from __future__ import annotations

import hashlib
from urllib.parse import urlencode

from ..config import config

PAYMENT_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def _md5(raw: str) -> str:
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _shp_suffix(shp: dict[str, str]) -> str:
    """Дополнительные параметры Shp_ включаются в подпись в алфавитном порядке."""
    return "".join(f":{k}={shp[k]}" for k in sorted(shp))


def build_payment_url(inv_id: int, amount_rub: float, description: str,
                      user_id: int, tariff: str) -> str:
    out_sum = f"{amount_rub:.2f}"
    shp = {"Shp_tariff": tariff, "Shp_user": str(user_id)}
    signature = _md5(
        f"{config.robokassa_login}:{out_sum}:{inv_id}:"
        f"{config.robokassa_password1}{_shp_suffix(shp)}"
    )
    params = {
        "MerchantLogin": config.robokassa_login,
        "OutSum": out_sum,
        "InvId": inv_id,
        "Description": description,
        "SignatureValue": signature,
        "Culture": "ru",
        "Encoding": "utf-8",
        **shp,
    }
    if config.robokassa_test:
        params["IsTest"] = 1
    return f"{PAYMENT_URL}?{urlencode(params)}"


def check_result_signature(out_sum: str, inv_id: str, signature: str,
                           shp: dict[str, str]) -> bool:
    """Проверка подписи ResultURL: MD5(OutSum:InvId:Пароль#2[:Shp_...])."""
    expected = _md5(
        f"{out_sum}:{inv_id}:{config.robokassa_password2}{_shp_suffix(shp)}"
    )
    return expected.lower() == (signature or "").lower()
