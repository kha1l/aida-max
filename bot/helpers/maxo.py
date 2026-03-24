"""Вспомогательные функции для работы с объектами `maxo`.

Здесь держим небольшие helpers, чтобы не размазывать по хендлерам
однотипную логику извлечения `chat_id`, имени пользователя и т.п.
"""

from __future__ import annotations

from typing import Any

from maxo.routing.updates import MessageCallback, MessageCreated


def resolve_message_chat_id(message: MessageCreated) -> int | None:
    """Возвращает `chat_id` из входящего сообщения MAX, если он доступен."""
    recipient = getattr(getattr(message, "message", None), "recipient", None)
    chat_id = getattr(recipient, "chat_id", None)
    return int(chat_id) if chat_id is not None else None


def resolve_callback_chat_id(callback: MessageCallback) -> int | None:
    """Возвращает `chat_id` из callback-события MAX, если он доступен."""
    recipient = getattr(getattr(callback, "unsafe_message", None), "recipient", None)
    chat_id = getattr(recipient, "chat_id", None)
    return int(chat_id) if chat_id is not None else None


def resolve_user_display_name(user: Any | None, *, default: str = "there") -> str:
    """Возвращает понятное имя пользователя для приветствий и логов."""
    if user is None:
        return default
    return (
        getattr(user, "fullname", None)
        or getattr(user, "first_name", None)
        or getattr(user, "name", None)
        or default
    )

