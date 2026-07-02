"""Слой доступа к данным (SQLite через aiosqlite)."""
from __future__ import annotations

from datetime import datetime, date

import aiosqlite

from .config import config
from .tariffs import DEFAULT_TARIFF

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id        INTEGER PRIMARY KEY,
    username       TEXT,
    tariff         TEXT NOT NULL DEFAULT 'free',
    tariff_until   TEXT,                 -- ISO дата окончания подписки
    tiktok_token   TEXT,                 -- access_token TikTok (OAuth)
    tiktok_open_id TEXT,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS uploads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    source_url TEXT,
    status     TEXT NOT NULL,            -- pending | done | failed
    day        TEXT NOT NULL,            -- YYYY-MM-DD (для суточной квоты)
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    tariff       TEXT NOT NULL,
    amount       REAL NOT NULL,
    currency     TEXT NOT NULL,
    charge_id    TEXT,
    created_at   TEXT NOT NULL
);
"""


async def init_db() -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.executescript(_SCHEMA)
        await db.commit()


async def get_or_create_user(user_id: int, username: str | None) -> dict:
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, tariff, created_at) VALUES (?, ?, ?, ?)",
                (user_id, username, DEFAULT_TARIFF, datetime.utcnow().isoformat()),
            )
            await db.commit()
            cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = await cur.fetchone()
        return dict(row)


async def set_tariff(user_id: int, tariff: str, until_iso: str) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "UPDATE users SET tariff = ?, tariff_until = ? WHERE user_id = ?",
            (tariff, until_iso, user_id),
        )
        await db.commit()


async def set_tiktok_token(user_id: int, token: str, open_id: str) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "UPDATE users SET tiktok_token = ?, tiktok_open_id = ? WHERE user_id = ?",
            (token, open_id, user_id),
        )
        await db.commit()


async def count_today_uploads(user_id: int) -> int:
    today = date.today().isoformat()
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM uploads WHERE user_id = ? AND day = ? AND status != 'failed'",
            (user_id, today),
        )
        (n,) = await cur.fetchone()
        return int(n)


async def add_upload(user_id: int, source_url: str, status: str) -> int:
    async with aiosqlite.connect(config.database_path) as db:
        cur = await db.execute(
            "INSERT INTO uploads (user_id, source_url, status, day, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, source_url, status, date.today().isoformat(),
             datetime.utcnow().isoformat()),
        )
        await db.commit()
        return cur.lastrowid


async def set_upload_status(upload_id: int, status: str) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute("UPDATE uploads SET status = ? WHERE id = ?", (status, upload_id))
        await db.commit()


async def add_payment(user_id: int, tariff: str, amount: float,
                      currency: str, charge_id: str) -> None:
    async with aiosqlite.connect(config.database_path) as db:
        await db.execute(
            "INSERT INTO payments (user_id, tariff, amount, currency, charge_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, tariff, amount, currency, charge_id, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def stats() -> dict:
    async with aiosqlite.connect(config.database_path) as db:
        db.row_factory = aiosqlite.Row
        users = (await (await db.execute("SELECT COUNT(*) c FROM users")).fetchone())["c"]
        uploads = (await (await db.execute("SELECT COUNT(*) c FROM uploads WHERE status='done'")).fetchone())["c"]
        revenue = (await (await db.execute("SELECT COALESCE(SUM(amount),0) s FROM payments")).fetchone())["s"]
        return {"users": users, "uploads": uploads, "revenue": revenue}
