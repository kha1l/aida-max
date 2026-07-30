"""Middleware работы с БД и контекстом пользователя для `aida_max`."""

from __future__ import annotations

from typing import Any

from loguru import logger
from maxo.routing.ctx import Ctx
from maxo.routing.interfaces.middleware import BaseMiddleware, NextMiddleware
from maxo.routing.signals.update import MaxoUpdate
from maxo.types import BotStarted, MessageCallback, MessageCreated
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.helpers.maxo import resolve_callback_chat_id, resolve_message_chat_id
from database.requests.users import get_user_context
from security_logging import pseudonymize


class DBSessionMiddleware(BaseMiddleware[MaxoUpdate[Any]]):
    """Открывает `AsyncSession` на время обработки одного update."""

    def __init__(self, session_maker: async_sessionmaker[AsyncSession]) -> None:
        self.session_maker = session_maker

    async def __call__(
        self,
        update: MaxoUpdate[Any],
        ctx: Ctx,
        next: NextMiddleware[MaxoUpdate[Any]],
    ) -> Any:
        async with self.session_maker() as session:
            ctx["session"] = session
            return await next(ctx)


class UserContextMiddleware(BaseMiddleware[MaxoUpdate[Any]]):
    """Подгружает контекст пользователя и кладет его в `ctx` для хендлеров."""

    @staticmethod
    def _resolve_chat_id(update: MaxoUpdate[Any], ctx: Ctx) -> int | None:
        """Пытается достать chat_id из ctx, а если его нет — из сырых MAX update-объектов."""
        event_chat = ctx.get("event_chat")
        current_chat_id = getattr(event_chat, "id", None)
        if current_chat_id is not None:
            return int(current_chat_id)

        event = ctx.get("event")
        if isinstance(event, MessageCallback):
            return resolve_callback_chat_id(event)
        if isinstance(event, MessageCreated):
            return resolve_message_chat_id(event)
        if isinstance(event, BotStarted):
            return int(event.chat_id)

        # На всякий случай пробуем и сам transport update, если `ctx["event"]`
        # не был обогащен ожидаемым объектом.
        if isinstance(update, MessageCallback):
            return resolve_callback_chat_id(update)
        if isinstance(update, MessageCreated):
            return resolve_message_chat_id(update)
        if isinstance(update, BotStarted):
            return int(update.chat_id)
        return None

    async def __call__(
        self,
        update: MaxoUpdate[Any],
        ctx: Ctx,
        next: NextMiddleware[MaxoUpdate[Any]],
    ) -> Any:
        session: AsyncSession | None = ctx.get("session")
        tg_user = ctx.get("event_from_user")
        if session is None or tg_user is None:
            return await next(ctx)

        current_chat_id = self._resolve_chat_id(update, ctx)
        user_ctx = await get_user_context(session, tg_user, current_chat_id)
        if user_ctx is None:
            logger.warning(
                "Пользователь не найден в базе данных",
                chat_hash=pseudonymize(current_chat_id),
                user_hash=pseudonymize(getattr(tg_user, "id", None)),
            )
        else:
            logger.success(
                "Пользователь успешно загружен из базы данных",
                chat_hash=pseudonymize(current_chat_id),
                user_hash=pseudonymize(getattr(tg_user, "id", None)),
            )

        ctx["user_ctx"] = user_ctx
        # В maxo ключ `ctx` зарезервирован самим dispatcher'ом, поэтому
        # пользовательский контекст кладем только в собственные поля.
        ctx["ctx_data"] = user_ctx
        return await next(ctx)
