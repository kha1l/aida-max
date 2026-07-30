"""Стартовые команды `aida_max` на базе maxo."""

from __future__ import annotations

from typing import Any, Callable
from urllib.parse import unquote

from loguru import logger
from maxo import Router
from maxo.routing.filters import CommandStart, DeeplinkFilter
from maxo.routing.facades import BotStartedFacade, MessageCreatedFacade
from maxo.types import BotStarted, MessageCreated

from bot.helpers.maxo import resolve_user_display_name
from bot.dialogs.texts import MenuTexts
from config import Config
from bot.keyboards.info import new_account
from bot.keyboards.menu import main_menu_keyboard
from database.requests.users import get_user_context
from security_logging import SERVICE_NAME, emit_security_event, pseudonymize
from services.i18n import tr
from services.max_auth import MaxBindError, bind_max_account

router = Router()


def _extract_legacy_account_payload(deeplink: str | None) -> tuple[int | None, str | None]:
    """Достает account_id из старого числового payload, если ссылка еще старого формата."""
    raw = unquote(str(deeplink or "").strip())
    if raw.isdigit():
        return int(raw), None
    return None, None


def _resolve_user_id(user: Any) -> int:
    return int(getattr(user, "id", None) or getattr(user, "user_id"))


def _resolve_username(user: Any) -> str:
    return str(getattr(user, "username", "") or "")


def _resolve_full_name(user: Any) -> str:
    return str(
        getattr(user, "fullname", None)
        or getattr(user, "first_name", None)
        or getattr(user, "name", None)
        or ""
    )


@router.bot_started(DeeplinkFilter())
async def deeplink_start_(
    bot_started: BotStarted,
    facade: BotStartedFacade,
    deeplink: str,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda s: s,
    event_from_user: Any | None = None,
    session: Any | None = None,
    config: Config | None = None,
) -> None:
    """Привязывает MAX-пользователя к account из deeplink и открывает меню."""
    max_user = event_from_user or bot_started.user
    user_name = resolve_user_display_name(max_user)
    current_chat_id = int(bot_started.chat_id)

    if session is None or config is None:
        emit_security_event(
            "auth_failed",
            service=SERVICE_NAME,
            source="max",
            actor=_resolve_user_id(max_user),
            object_name="account_binding",
            result="failure",
            reason_code="runtime_context_missing",
        )
        await facade.send_message(
            "Не удалось завершить авторизацию MAX. Пожалуйста, попробуйте еще раз.",
        )
        return

    deeplink_payload = unquote(str(deeplink).strip())
    account_id, account_name = _extract_legacy_account_payload(deeplink_payload)

    try:
        await bind_max_account(
            bind_url=config.max_auth.bind_url,
            deeplink=deeplink_payload,
            account_id=account_id,
            account_name=account_name,
            max_id=_resolve_user_id(max_user),
            chat_id=current_chat_id,
            username=_resolve_username(max_user),
            name=_resolve_full_name(max_user),
            timeout_seconds=config.max_auth.request_timeout_seconds,
        )
        user_ctx = await get_user_context(session, max_user, current_chat_id)
        if user_ctx:
            emit_security_event(
                "auth_succeeded",
                service=SERVICE_NAME,
                source="max",
                actor=_resolve_user_id(max_user),
                object_name="account_binding",
                result="success",
                reason_code="deeplink_binding_succeeded",
            )
            logger.info(
                "MAX user successfully bound to account from deeplink",
                chat_hash=pseudonymize(current_chat_id),
                user_hash=pseudonymize(_resolve_user_id(max_user)),
                object="account_binding",
            )
        else:
            emit_security_event(
                "auth_failed",
                service=SERVICE_NAME,
                source="max",
                actor=_resolve_user_id(max_user),
                object_name="account_binding",
                result="failure",
                reason_code="user_context_unavailable",
            )
            logger.warning(
                "MAX account binding completed without user context",
                chat_hash=pseudonymize(current_chat_id),
                user_hash=pseudonymize(_resolve_user_id(max_user)),
                object="account_binding",
            )
    except MaxBindError as exc:
        emit_security_event(
            "auth_failed",
            service=SERVICE_NAME,
            source="max",
            actor=_resolve_user_id(max_user),
            object_name="account_binding",
            result="failure",
            reason_code="deeplink_binding_failed",
        )
        logger.warning(
            "Failed to bind MAX user to account from deeplink",
            chat_hash=pseudonymize(current_chat_id),
            user_hash=pseudonymize(_resolve_user_id(max_user)),
            object="account_binding",
            error_type=type(exc).__name__,
        )
        await facade.send_message(
            "Не удалось завершить авторизацию MAX. Пожалуйста, начните авторизацию заново из marketplace.",
        )
        return

    if not user_ctx:
        await facade.send_message(
            tr(_, MenuTexts.AUTH_REQUIRED_MESSAGE, user_name=user_name),
            keyboard=new_account(_),
        )
        return

    await facade.send_message(
        tr(_, MenuTexts.MAIN_GREETING, user_name=user_name),
        keyboard=main_menu_keyboard(_),
    )


@router.bot_started()
async def bot_started_(
    bot_started: BotStarted,
    facade: BotStartedFacade,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda s: s,
    event_from_user: Any | None = None,
) -> None:
    """Открывает меню при обычном запуске MAX-бота без deeplink."""
    max_user = event_from_user or bot_started.user
    user_name = resolve_user_display_name(max_user)

    if not user_ctx:
        await facade.send_message(
            tr(_, MenuTexts.AUTH_REQUIRED_MESSAGE, user_name=user_name),
            keyboard=new_account(_),
        )
        return

    await facade.send_message(
        tr(_, MenuTexts.MAIN_GREETING, user_name=user_name),
        keyboard=main_menu_keyboard(_),
    )


@router.message_created(CommandStart())
async def start_(
    message: MessageCreated,
    facade: MessageCreatedFacade,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda s: s,
    event_from_user: Any | None = None,
) -> None:
    """Открывает меню по текстовой команде `/start`."""
    user_name = resolve_user_display_name(event_from_user)

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
