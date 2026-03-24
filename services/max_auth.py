"""Клиент для привязки MAX-пользователя к account во внешнем auth-сервисе."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import aiohttp


class MaxBindError(RuntimeError):
    """Ошибка привязки MAX-пользователя к account."""


@dataclass(slots=True)
class MaxBindResult:
    """Результат успешной привязки пользователя."""

    ok: bool
    user_id: int
    account_id: int
    chat_id: int
    language: str


async def bind_max_account(
    *,
    bind_url: str | None,
    account_id: int,
    max_id: int,
    chat_id: int | None = None,
    username: str = "",
    name: str = "",
    timeout_seconds: int = 15,
) -> MaxBindResult:
    """Вызывает внешний bind endpoint и связывает MAX user с account."""
    if not bind_url:
        raise MaxBindError("MAX_BIND_URL is not configured")

    payload = {
        "account_id": account_id,
        "max_id": max_id,
        "chat_id": chat_id,
        "username": username,
        "name": name,
    }

    timeout = aiohttp.ClientTimeout(total=timeout_seconds)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(bind_url, json=payload) as response:
                data: dict[str, Any] = await response.json(content_type=None)
                if response.status >= 400:
                    raise MaxBindError(str(data.get("error") or f"HTTP {response.status}"))
    except aiohttp.ClientError as exc:
        raise MaxBindError(f"Bind request failed: {exc}") from exc

    if not data.get("ok"):
        raise MaxBindError(str(data.get("error") or "Bind failed"))

    return MaxBindResult(
        ok=True,
        user_id=int(data["user_id"]),
        account_id=int(data["account_id"]),
        chat_id=int(data["chat_id"]),
        language=str(data.get("language") or "ru"),
    )
