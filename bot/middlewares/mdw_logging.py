"""Middleware логирования для `aida_max` на базе `maxo`."""

from __future__ import annotations

from typing import Any

from loguru import logger
from maxo.routing.ctx import Ctx
from maxo.routing.interfaces.middleware import BaseMiddleware, NextMiddleware
from maxo.routing.signals.update import MaxoUpdate
from maxo.routing.updates.message_callback import MessageCallback
from maxo.routing.updates.message_created import MessageCreated


def _is_start_message(update: MaxoUpdate[Any]) -> bool:
    """Проверяет, что событие является `/start`."""
    inner = update.update
    return isinstance(inner, MessageCreated) and (inner.text or "").strip().startswith("/start")


class LoggingMiddleware(BaseMiddleware[MaxoUpdate[Any]]):
    """Логирует входящие maxo-update и ошибки обработки."""

    async def __call__(
        self,
        update: MaxoUpdate[Any],
        ctx: Ctx,
        next: NextMiddleware[MaxoUpdate[Any]],
    ) -> Any:
        """Добавляет в лог базовый контекст чата и пользователя."""
        log = logger
        inner = update.update
        update_context = ctx.get("update_context")

        try:
            if isinstance(inner, MessageCreated):
                if _is_start_message(update):
                    log = log.bind(
                        update_type="message_created",
                        chat_id=getattr(update_context, "chat_id", None),
                        user_id=getattr(update_context, "user_id", None),
                    )
                    log.info("message", text=inner.text)
            elif isinstance(inner, MessageCallback):
                log = log.bind(
                    update_type="message_callback",
                    chat_id=getattr(update_context, "chat_id", None),
                    user_id=getattr(update_context, "user_id", None),
                    callback_data=inner.callback.payload,
                )
                log.info("callback")
            else:
                log = log.bind(
                    update_type=inner.__class__.__name__,
                    chat_id=getattr(update_context, "chat_id", None),
                    user_id=getattr(update_context, "user_id", None),
                )
                log.info("update")

            return await next(ctx)
        except Exception:
            log.exception("failed")
            raise
