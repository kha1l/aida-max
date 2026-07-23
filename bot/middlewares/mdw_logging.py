"""Middleware логирования для `aida_max` на базе `maxo`."""

from __future__ import annotations

from typing import Any

from loguru import logger
from maxo.routing.ctx import Ctx
from maxo.routing.interfaces.middleware import BaseMiddleware, NextMiddleware
from maxo.routing.signals.update import MaxoUpdate
from maxo.routing.updates.bot_started import BotStarted
from maxo.routing.updates.message_callback import MessageCallback
from maxo.routing.updates.message_created import MessageCreated
from security_logging import emit_security_event, pseudonymize


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
                    user_id = getattr(update_context, "user_id", None)
                    update_id = getattr(inner, "update_id", None)
                    emit_security_event(
                        "auth_succeeded",
                        service="aida-max",
                        source="max",
                        actor=user_id,
                        object_name="polling_update",
                        result="success",
                        reason_code="platform_update_verified",
                        request_id=str(update_id) if update_id is not None else None,
                        trace_id=str(update_id) if update_id is not None else None,
                    )
                    log = log.bind(
                        update_type="message_created",
                        chat_hash=pseudonymize(getattr(update_context, "chat_id", None)),
                        user_hash=pseudonymize(getattr(update_context, "user_id", None)),
                    )
                    log.info("message received")
            elif isinstance(inner, BotStarted):
                log = log.bind(
                    update_type="bot_started",
                    chat_hash=pseudonymize(getattr(update_context, "chat_id", None)),
                    user_hash=pseudonymize(getattr(update_context, "user_id", None)),
                )
                log.info("bot started")
            elif isinstance(inner, MessageCallback):
                log = log.bind(
                    update_type="message_callback",
                    chat_hash=pseudonymize(getattr(update_context, "chat_id", None)),
                    user_hash=pseudonymize(getattr(update_context, "user_id", None)),
                )
                log.info("callback")
            else:
                log = log.bind(
                    update_type=inner.__class__.__name__,
                    chat_hash=pseudonymize(getattr(update_context, "chat_id", None)),
                    user_hash=pseudonymize(getattr(update_context, "user_id", None)),
                )
                log.info("update")

            return await next(ctx)
        except Exception:
            log.exception("failed")
            raise
