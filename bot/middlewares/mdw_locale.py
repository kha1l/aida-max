"""I18n middleware для `aida_max`."""

from __future__ import annotations

from typing import Any

from maxo.routing.ctx import Ctx
from maxo.routing.interfaces.middleware import BaseMiddleware, NextMiddleware
from maxo.routing.signals.update import MaxoUpdate
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests.settings import (
    get_chat_language,
    get_default_user_language,
    get_user_settings,
)
from services.i18n import get_translator


class I18nMiddleware(BaseMiddleware[MaxoUpdate[Any]]):
    """Подкладывает функцию перевода и настройки языка в `ctx`."""

    async def __call__(
        self,
        update: MaxoUpdate[Any],
        ctx: Ctx,
        next: NextMiddleware[MaxoUpdate[Any]],
    ) -> Any:
        session: AsyncSession | None = ctx.get("session")
        tg_user = ctx.get("event_from_user")
        event_chat = ctx.get("event_chat")

        if session is None or tg_user is None:
            gettext_fn = get_translator(language="ru")
            ctx["_"] = gettext_fn
            ctx["i18n_gettext"] = gettext_fn
            return await next(ctx)

        chat_id = getattr(event_chat, "id", None)
        chat_language = await get_chat_language(session, chat_id) if chat_id is not None else None
        settings = await get_user_settings(session, tg_user)

        if chat_language:
            language = chat_language
        else:
            language = await get_default_user_language(session, tg_user)

        gettext_fn = get_translator(language=language)
        ctx["_"] = gettext_fn
        ctx["i18n_gettext"] = gettext_fn
        ctx["settings"] = settings
        return await next(ctx)
