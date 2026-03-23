"""Глобальная обработка ошибок для базового runtime `aida_max`."""

from __future__ import annotations

from typing import Callable

from loguru import logger
from maxo import Router
from maxo.routing.updates import ErrorEvent, MessageCallback, MessageCreated
from maxo.utils.facades import ErrorEventFacade

from bot.dialogs.texts import MenuTexts
from services.i18n import tr

router = Router()


@router.error()
async def on_error(
    error: ErrorEvent,
    facade: ErrorEventFacade,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Логирует неожиданные ошибки и мягко сообщает о них пользователю."""
    logger.exception("Unhandled exception in maxo handler", error=repr(error.error))

    event = error.event
    message = tr(_, MenuTexts.GENERIC_ERROR)

    if isinstance(event, MessageCallback):
        await facade.bot.answer_on_callback(
            callback_id=event.callback_id,
            notification=message,
        )
        return

    if isinstance(event, MessageCreated):
        await facade.bot.send_message(chat_id=event.message.recipient.chat_id, text=message)
