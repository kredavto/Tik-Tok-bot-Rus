"""Скачивание исходного видео (Reels / TikTok / прочее) по ссылке.

Используется yt-dlp. Скачивание идёт напрямую (Instagram/etc. в РФ доступны),
а вот отдача в TikTok — уже через прокси (см. services/tiktok.py).
"""
from __future__ import annotations

import asyncio
import os
import uuid

import yt_dlp

DOWNLOAD_DIR = "downloads"
MAX_BYTES = 300 * 1024 * 1024  # 300 МБ — потолок для одного видео


class DownloadError(Exception):
    pass


def _download_sync(url: str) -> str:
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    out_tmpl = os.path.join(DOWNLOAD_DIR, f"{uuid.uuid4().hex}.%(ext)s")
    opts = {
        "outtmpl": out_tmpl,
        "format": "mp4/bestvideo[ext=mp4]+bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": MAX_BYTES,
        "merge_output_format": "mp4",
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = ydl.prepare_filename(info)
    if not os.path.exists(path):
        # merge мог изменить расширение на .mp4
        base, _ = os.path.splitext(path)
        path = base + ".mp4"
    if not os.path.exists(path):
        raise DownloadError("Не удалось скачать видео по ссылке.")
    return path


async def download_video(url: str) -> str:
    """Скачивает видео и возвращает путь к локальному файлу."""
    try:
        return await asyncio.to_thread(_download_sync, url)
    except DownloadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DownloadError(f"Ошибка скачивания: {exc}") from exc
