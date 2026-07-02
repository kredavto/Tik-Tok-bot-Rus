# TikTok Uploader Bot (RU) — Telegram-бот с монетизацией

Телеграм-бот для загрузки вертикальных видео (Reels / Shorts / клипы) в **TikTok
из России в обход региональных ограничений**. Монетизация — платные тарифы с
суточными лимитами загрузок.

## Как это работает и что с ограничениями РФ

С марта 2022 TikTok **отключил загрузку контента для пользователей из России**
(«закон о фейках»). Просмотр работает, а публикация — нет: при попытке отдать
видео с российской геолокации аккаунт получает shadowban (0 просмотров) или блок.

Бот обходит это так:

1. **Официальный TikTok Content Posting API.** Пользователь один раз привязывает
   свой аккаунт TikTok по OAuth, бот получает `access_token` и публикует ролики
   от его имени легальным API, а не парсингом.
2. **Прокси вне РФ.** Весь исходящий трафик к TikTok (OAuth + загрузка файла)
   маршрутизируется через `TIKTOK_PROXY` — сервер за пределами России, чтобы
   TikTok не определил российскую геолокацию. Исходное видео скачивается напрямую.

> ⚠️ **Важно (юридическая/ToS оговорка).** Обход гео-ограничений может нарушать
> Условия использования TikTok. Использование бота, оплату налогов с выручки и
> соблюдение законодательства РФ и стран, где работает прокси, каждый оператор
> берёт на себя. Для приёма платежей и работы Content Posting API требуется
> одобренное приложение на [developers.tiktok.com](https://developers.tiktok.com).

## Тарифы

| Тариф     | Загрузок в сутки | Цена     |
|-----------|------------------|----------|
| Free      | 1                | $5.9     |
| PRO       | 3                | $9.9     |
| Business  | 10               | $19.9    |

Цены заданы в `app/tariffs.py`. Подписка — на 30 дней, суточный счётчик
сбрасывается по календарным суткам.

## Оплата

Поддерживаются два способа (выбор через `.env`):

- **Telegram Payments** (карты — ЮKassa для РФ, Stripe для валюты): задайте
  `PAYMENT_PROVIDER_TOKEN` и `CURRENCY`.
- **Telegram Stars (XTR)**: оставьте `PAYMENT_PROVIDER_TOKEN` пустым — прайс
  автоматически пересчитается в звёзды.

## Установка

```bash
cp .env.example .env      # заполните BOT_TOKEN и остальное
pip install -r requirements.txt
python main.py
```

Или в Docker:

```bash
cp .env.example .env
docker compose up -d --build
```

## Переменные окружения

См. `.env.example`. Ключевые:

- `BOT_TOKEN` — токен от [@BotFather](https://t.me/BotFather).
- `ADMIN_IDS` — id админов (команды `/stats`, `/grant`).
- `TIKTOK_PROXY` — прокси вне РФ (`http://` или `socks5://`).
- `TIKTOK_CLIENT_KEY` / `TIKTOK_CLIENT_SECRET` / `TIKTOK_REDIRECT_URI` —
  данные приложения TikTok для OAuth и Content Posting API.

## Структура

```
main.py                  запуск (polling + OAuth-сервер)
app/
  config.py              конфигурация из окружения
  tariffs.py             тарифные планы
  database.py            SQLite: пользователи, загрузки, платежи, квоты
  keyboards.py           inline-меню
  oauth_server.py        HTTP callback для привязки TikTok
  handlers/
    menu.py              меню, профиль, привязка TikTok
    upload.py            приём видео/ссылки, проверка квоты, загрузка
    payments.py          тарифы и оплата (Payments/Stars)
    admin.py             /stats, /grant
  services/
    downloader.py        скачивание исходного видео (yt-dlp)
    tiktok.py            Content Posting API + маршрутизация через прокси
```

## Команды бота

- `/start` — меню.
- `/stats` — статистика (админ).
- `/grant <user_id> <free|pro|business>` — выдать тариф вручную (админ).

## Настройка BotFather

1. Создайте бота, получите `BOT_TOKEN`.
2. Для оплаты картами: `/mybots → Payments` → подключите провайдера, скопируйте
   токен в `PAYMENT_PROVIDER_TOKEN`.
3. Для Stars ничего подключать не нужно.
