"""Загрузка видео в TikTok через официальный Content Posting API.

Обход региональных ограничений РФ:
  TikTok с марта 2022 блокирует загрузку контента из России. Поэтому ВЕСЬ
  исходящий трафик к api/open api TikTok маршрутизируется через прокси
  (config.tiktok_proxy) — сервер вне РФ. Пользователь один раз привязывает
  свой аккаунт TikTok по OAuth (endpoint см. build_oauth_url), бот хранит
  access_token и грузит видео от его имени.

Документация: https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

import aiohttp

from ..config import config

OAUTH_AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
OAUTH_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
INIT_UPLOAD = "https://open.tiktokapis.com/v2/post/publish/video/init/"
SCOPES = "user.info.basic,video.upload,video.publish"


class TikTokError(Exception):
    pass


def build_oauth_url(state: str) -> str:
    """Ссылка, по которой пользователь привязывает аккаунт TikTok."""
    params = {
        "client_key": config.tiktok_client_key,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": config.tiktok_redirect_uri,
        "state": state,
    }
    return f"{OAUTH_AUTHORIZE}?{urlencode(params)}"


def _proxy() -> str | None:
    return config.tiktok_proxy or None


async def exchange_code(code: str) -> dict:
    """Меняет OAuth-код на access_token (запрос идёт через прокси вне РФ)."""
    data = {
        "client_key": config.tiktok_client_key,
        "client_secret": config.tiktok_client_secret,
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config.tiktok_redirect_uri,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(OAUTH_TOKEN, data=data, proxy=_proxy()) as r:
            body = await r.json()
    if "access_token" not in body:
        raise TikTokError(f"OAuth ошибка: {body}")
    return body


async def upload_video(access_token: str, file_path: str, caption: str = "") -> dict:
    """Загружает локальный файл в TikTok.

    Использует FILE_UPLOAD source: сначала init (получаем upload_url),
    затем PUT самого файла — всё через прокси вне РФ, чтобы TikTok не
    определил российскую геолокацию и не наложил shadowban.
    """
    if not access_token:
        raise TikTokError("Аккаунт TikTok не привязан. Нажмите «Привязать TikTok».")

    size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    init_payload = {
        "post_info": {
            "title": caption[:2200],
            "privacy_level": "SELF_ONLY",  # безопасный дефолт; меняется в настройках
            "disable_comment": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    }

    async with aiohttp.ClientSession() as s:
        async with s.post(INIT_UPLOAD, json=init_payload, headers=headers,
                          proxy=_proxy()) as r:
            init = await r.json()
        err = (init.get("error") or {})
        if err.get("code") not in (None, "ok"):
            raise TikTokError(f"init ошибка: {err}")
        upload_url = init["data"]["upload_url"]

        with open(file_path, "rb") as f:
            content = f.read()
        put_headers = {
            "Content-Type": "video/mp4",
            "Content-Range": f"bytes 0-{size - 1}/{size}",
            "Content-Length": str(size),
        }
        async with s.put(upload_url, data=content, headers=put_headers,
                         proxy=_proxy()) as r:
            if r.status not in (200, 201):
                raise TikTokError(f"Ошибка отдачи файла: HTTP {r.status}")

    return {"publish_id": init["data"].get("publish_id")}
