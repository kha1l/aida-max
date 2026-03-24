"""Middleware работы с БД и контекстом пользователя для `aida_max`."""

from __future__ import annotations

from typing import Any

from loguru import logger
from maxo.routing.ctx import Ctx
from maxo.routing.interfaces.middleware import BaseMiddleware, NextMiddleware
from maxo.routing.signals.update import MaxoUpdate
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.requests.users import get_user_context


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

        event_chat = ctx.get("event_chat")
        current_chat_id = getattr(event_chat, "id", None)
        user_ctx = await get_user_context(session, tg_user, current_chat_id)
        if user_ctx is None:
            logger.warning(
                "Пользователь не найден в базе данных",
                platform_id=current_chat_id,
                max_id=getattr(tg_user, "id", None),
                user_id=getattr(tg_user, "id", None),
                chat_id=current_chat_id,
            )
        else:
            logger.success(
                "Пользователь успешно загружен из базы данных",
                platform_id=current_chat_id,
                max_id=getattr(tg_user, "id", None),
                user_id=user_ctx.get("user_id"),
            )

        ctx["user_ctx"] = user_ctx
        # В maxo ключ `ctx` зарезервирован самим dispatcher'ом, поэтому
        # пользовательский контекст кладем только в собственные поля.
        ctx["ctx_data"] = user_ctx
        return await next(ctx)
