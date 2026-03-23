"""Стартовые команды `aida_max` на базе maxo."""

from __future__ import annotations

from typing import Any, Callable

from maxo import Router
from maxo.routing.filters import CommandStart
from maxo.routing.updates import MessageCreated
from maxo.utils.facades import MessageCreatedFacade

from bot.dialogs.texts import MenuTexts
from bot.keyboards.info import new_account
from bot.keyboards.menu import main_menu_keyboard
from services.i18n import tr

router = Router()


@router.message_created(CommandStart())
async def start_(
    message: MessageCreated,
    facade: MessageCreatedFacade,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda s: s,
    event_from_user: Any | None = None,
) -> None:
    """Минимальный `/start` для первого рабочего этапа миграции на maxo."""
    user_name = getattr(event_from_user, "fullname", None) or getattr(event_from_user, "first_name", None) or "there"

    if not user_ctx:
        await facade.answer_text(
            tr(_, MenuTexts.AUTH_REQUIRED_MESSAGE, user_name=user_name),
            keyboard=new_account(_),
        )
        return

    await facade.answer_text(
        tr(_, MenuTexts.MAIN_GREETING, user_name=user_name),
        keyboard=main_menu_keyboard(_),
    )
