"""Стартовые команды `aida_max` на базе maxo."""

from __future__ import annotations

from typing import Any, Callable

from loguru import logger
from maxo import Router
from maxo.routing.filters import CommandStart
from maxo.routing.updates import MessageCreated
from maxo.utils.facades import MessageCreatedFacade

from bot.helpers.maxo import resolve_message_chat_id, resolve_user_display_name
from bot.dialogs.texts import MenuTexts
from config import Config
from bot.keyboards.info import new_account
from bot.keyboards.menu import main_menu_keyboard
from database.requests.users import get_user_context
from services.i18n import tr
from services.max_auth import MaxBindError, bind_max_account

router = Router()


def _extract_start_payload(text: str | None) -> str | None:
    """Достает payload из команды `/start <payload>`, если он есть."""
    raw = (text or "").strip()
    if not raw:
        return None
    parts = raw.split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip() or None


@router.message_created(CommandStart())
async def start_(
    message: MessageCreated,
    facade: MessageCreatedFacade,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda s: s,
    event_from_user: Any | None = None,
    session: Any | None = None,
    config: Config | None = None,
) -> None:
    """Стартовый `/start`: при наличии payload связывает MAX user с account и открывает меню."""
    user_name = resolve_user_display_name(event_from_user)
    start_payload = _extract_start_payload(message.text)
    # Для MAX главным идентификатором диалога считаем именно `chat_id`,
    # потому что в него потом будут приходить все отправки из RabbitMQ.
    current_chat_id = resolve_message_chat_id(message)

    if not user_ctx and start_payload and start_payload.isdigit() and event_from_user is not None and session is not None and config is not None:
        try:
            await bind_max_account(
                bind_url=config.max_auth.bind_url,
                account_id=int(start_payload),
                max_id=int(getattr(event_from_user, "id")),
                chat_id=int(current_chat_id) if current_chat_id is not None else None,
                username=str(getattr(event_from_user, "username", "") or ""),
                name=str(getattr(event_from_user, "fullname", None) or getattr(event_from_user, "first_name", None) or ""),
                timeout_seconds=config.max_auth.request_timeout_seconds,
            )
            user_ctx = await get_user_context(
                session,
                event_from_user,
                int(current_chat_id) if current_chat_id is not None else None,
            )
            logger.info(
                "MAX user successfully bound to account",
                platform_id=int(current_chat_id) if current_chat_id is not None else None,
                max_id=getattr(event_from_user, "id", None),
                account_id=int(start_payload),
                user_id=user_ctx.get("user_id") if user_ctx else None,
            )
        except MaxBindError as exc:
            logger.warning(
                "Failed to bind MAX user to account",
                platform_id=int(current_chat_id) if current_chat_id is not None else None,
                max_id=getattr(event_from_user, "id", None),
                account_id=int(start_payload),
                error=str(exc),
            )
            await facade.answer_text(
                "Не удалось завершить авторизацию MAX. Пожалуйста, начните авторизацию заново из marketplace.",
            )
            return

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
