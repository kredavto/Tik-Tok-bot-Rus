"""Загрузка видео в TikTok через официальный Content Posting API.

Обход региональных ограничений РФ:
  TikTok с марта 2022 блокирует загрузку контента из России. Поэтому ВЕСЬ
  исходящий трафик к open api TikTok маршрутизируется через прокси
  (config.tiktok_proxy) — сервер вне РФ. На нашем сервере в Нидерландах/через
  VPN прокси не нужен (TIKTOK_PROXY пустой). Пользователь один раз привязывает
  свой аккаунт TikTok по OAuth, бот хранит access_token и грузит видео от его имени.

Два режима загрузки (TIKTOK_UPLOAD_MODE):
  - "draft"  — заливает видео в «Черновики»/инбокс пользователя (scope video.upload).
               Работает в sandbox и без полного аудита приложения. Пользователь
               завершает публикацию в приложении TikTok. Это дефолт.
  - "direct" — прямая публикация в профиль (scope video.publish, Direct Post).
               Для публичных видео требует аудит приложения; до аудита — только
               приватно (SELF_ONLY) и для тест-аккаунтов.

Docs: https://developers.tiktok.com/doc/content-posting-api-reference-upload-video
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

import aiohttp

from ..config import config

OAUTH_AUTHORIZE = "https://www.tiktok.com/v2/auth/authorize/"
OAUTH_TOKEN = "https://open.tiktokapis.com/v2/oauth/token/"
DIRECT_INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"
INBOX_INIT = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
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
    """Меняет OAuth-код на access_token (запрос через прокси, если задан)."""
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


async def refresh_token(refresh: str) -> dict:
    """Обновляет access_token по refresh_token."""
    data = {
        "client_key": config.tiktok_client_key,
        "client_secret": config.tiktok_client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh,
    }
    async with aiohttp.ClientSession() as s:
        async with s.post(OAUTH_TOKEN, data=data, proxy=_proxy()) as r:
            body = await r.json()
    if "access_token" not in body:
        raise TikTokError(f"Refresh ошибка: {body}")
    return body


def _err_text(payload: dict) -> str:
    err = payload.get("error") or {}
    code = err.get("code")
    msg = err.get("message") or ""
    return f"{code}: {msg}".strip(": ")


async def upload_video(access_token: str, file_path: str, caption: str = "") -> dict:
    """Загружает локальный файл в TikTok согласно TIKTOK_UPLOAD_MODE.

    Оба режима: сначала init (получаем upload_url), затем PUT самого файла —
    всё через прокси (если задан), чтобы TikTok не определил гео РФ.
    """
    if not access_token:
        raise TikTokError("Аккаунт TikTok не привязан. Нажмите «Привязать TikTok».")

    size = os.path.getsize(file_path)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    source_info = {
        "source": "FILE_UPLOAD",
        "video_size": size,
        "chunk_size": size,
        "total_chunk_count": 1,
    }

    if config.tiktok_upload_mode == "direct":
        init_url = DIRECT_INIT
        payload = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": "SELF_ONLY",
                "disable_comment": False,
            },
            "source_info": source_info,
        }
    else:  # draft / inbox
        init_url = INBOX_INIT
        payload = {"source_info": source_info}

    async with aiohttp.ClientSession() as s:
        async with s.post(init_url, json=payload, headers=headers, proxy=_proxy()) as r:
            init = await r.json()
        err = _err_text(init)
        if err and not err.startswith("ok"):
            raise TikTokError(f"init: {err}")
        data = init.get("data") or {}
        upload_url = data.get("upload_url")
        if not upload_url:
            raise TikTokError(f"init без upload_url: {init}")

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

    return {
        "mode": config.tiktok_upload_mode,
        "publish_id": data.get("publish_id"),
    }
