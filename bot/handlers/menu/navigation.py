"""Навигация по главным разделам меню `aida_max`."""

from __future__ import annotations

from typing import Callable

from maxo import Router
from maxo.enums import TextFormat
from maxo.routing.updates import MessageCallback
from maxo.utils.facades import MessageCallbackFacade

from bot.callback.menu import LanguagePayload, MainMenuPayload, SectionPayload, SettingsPayload
from bot.dialogs.texts import MenuTexts
from bot.keyboards.live_data import build_live_units_keyboard
from bot.keyboards.menu import language_menu_keyboard, main_menu_keyboard, settings_menu_keyboard
from bot.keyboards.report_selection import build_report_units_keyboard
from database.requests.orders import get_orders_by_post
from database.requests.settings import set_chat_language_for_user
from services.i18n import setup_i18n, tr

from .common import (
    LIVE_DATA_ITEMS,
    NOTIFICATION_ITEMS,
    REPORT_ITEMS,
    available_units,
    live_data_title,
    main_menu_text,
    no_locations_message,
    require_callback_chat_id,
    section_keyboard,
    section_title,
    settings_text,
    subscription_title,
)

router = Router()


@router.message_callback(MainMenuPayload.filter())
async def on_main_menu(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: MainMenuPayload,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Обрабатывает простые действия главного меню."""
    action = payload.action

    if action == "settings":
        await facade.edit_message(
            text=settings_text(_, user_ctx),
            keyboard=settings_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        return

    if action == "close":
        await facade.delete_message()
        await facade.answer_text(_(MenuTexts.EXIT_MESSAGE))
        return

    if action in {"notifications", "reports", "operations"}:
        await facade.edit_message(
            text=section_title(_, action),
            keyboard=section_keyboard(_, action),
            format=TextFormat.HTML,
        )
        return

    await facade.callback_answer(notification=_(MenuTexts.NOT_IMPLEMENTED_YET))


@router.message_callback(SettingsPayload.filter())
async def on_settings(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: SettingsPayload,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Открывает экран выбора языка или возвращает пользователя назад."""
    if payload.action == "language":
        await facade.edit_message(
            text=_(MenuTexts.LANGUAGE_TITLE),
            keyboard=language_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        return

    await facade.edit_message(
        text=main_menu_text(_),
        keyboard=main_menu_keyboard(_),
        format=TextFormat.HTML,
    )


@router.message_callback(SectionPayload.filter())
async def on_section(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: SectionPayload,
    state,
    session,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Навигация по разделам Notifications / Reports / Live data."""
    if payload.item == "back":
        target_section = "notifications" if payload.section == "stops" else None
        if target_section is not None:
            await facade.edit_message(
                text=section_title(_, target_section),
                keyboard=section_keyboard(_, target_section),
                format=TextFormat.HTML,
            )
            return
        await facade.edit_message(
            text=main_menu_text(_),
            keyboard=main_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        return

    if payload.section == "operations" and payload.item in LIVE_DATA_ITEMS:
        units = available_units(user_ctx)
        if not units:
            await facade.callback_answer(notification=no_locations_message(_, user_ctx))
            return

        await state.update_data(live_operation=payload.item, live_selected=[])
        await facade.edit_message(
            text=live_data_title(_, payload.item),
            keyboard=build_live_units_keyboard(
                operation=payload.item,
                units=units,
                selected=set(),
                translate=_,
            ),
            format=TextFormat.HTML,
        )
        return

    if payload.section == "notifications" and payload.item == "stops":
        await facade.edit_message(
            text=section_title(_, "stops"),
            keyboard=section_keyboard(_, "stops"),
            format=TextFormat.HTML,
        )
        return

    if payload.section in {"reports", "notifications", "stops"} and payload.item in (REPORT_ITEMS | NOTIFICATION_ITEMS):
        units = available_units(user_ctx)
        if not units:
            await facade.callback_answer(notification=no_locations_message(_, user_ctx))
            return

        chat_id = require_callback_chat_id(callback)
        orders = await get_orders_by_post(session, chat_id, payload.item, None)
        selected = {unit_uuid for order in orders for unit_uuid in (order.uuids or [])}
        await state.update_data(
            selection_section=payload.section,
            selection_post=payload.item,
            selection_selected=sorted(selected),
            report_post=payload.item,
            report_selected=sorted(selected),
        )
        await facade.edit_message(
            text=subscription_title(_, payload.item),
            keyboard=build_report_units_keyboard(
                post=payload.item,
                units=units,
                selected=selected,
                translate=_,
            ),
            format=TextFormat.HTML,
        )
        return

    await facade.callback_answer(notification=_(MenuTexts.UNIT_SELECTION_NOT_READY))


@router.message_callback(LanguagePayload.filter())
async def on_language_selected(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: LanguagePayload,
    session,
    event_from_user,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Сохраняет язык для чата и переоткрывает главное меню на новом языке."""
    chat_id = require_callback_chat_id(callback)
    await set_chat_language_for_user(
        session=session,
        tg_user=event_from_user,
        chat_id=chat_id,
        country=payload.code,
    )

    translator = setup_i18n(payload.code).gettext
    await facade.edit_message(
        text=tr(translator, MenuTexts.LANGUAGE_CHANGED),
        keyboard=main_menu_keyboard(translator),
        format=TextFormat.HTML,
    )
    await facade.callback_answer(notification=tr(translator, MenuTexts.LANGUAGE_CHANGED))
