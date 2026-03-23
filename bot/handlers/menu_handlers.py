"""Простые callback-обработчики главного меню и настроек на `maxo`."""

from __future__ import annotations

from typing import Callable

from loguru import logger
from maxo import Router
from maxo.enums import TextFormat
from maxo.routing.updates import MessageCallback
from maxo.utils.facades import MessageCallbackFacade

from bot.callback.live_data import LiveUnitsActionPayload, LiveUnitTogglePayload
from bot.callback.menu import LanguagePayload, MainMenuPayload, SectionPayload, SettingsPayload
from bot.callback.report_selection import ReportUnitsActionPayload, ReportUnitTogglePayload
from bot.dialogs.data import POST
from bot.dialogs.texts import MenuTexts
from bot.keyboards.live_data import build_live_units_keyboard
from bot.keyboards.menu import (
    language_menu_keyboard,
    live_data_menu_keyboard,
    main_menu_keyboard,
    notifications_menu_keyboard,
    reports_menu_keyboard,
    settings_menu_keyboard,
    stops_menu_keyboard,
)
from bot.keyboards.report_selection import build_report_units_keyboard
from database.requests.orders import delete_order, get_orders_by_post, upsert_order
from database.requests.settings import set_chat_language_for_user
from services.i18n import setup_i18n, tr

router = Router()
LIVE_DATA_ITEMS = {"tracking", "metrics", "revenue", "stock"}
NOTIFICATION_ITEMS = {
    "birthday",
    "stops_rest",
    "stops_key_ings",
    "stops_ings",
    "stops_sector",
    "tickets",
    "staff",
    "refusal",
    "defect",
}
REPORT_ITEMS = {"couriers", "stationary", "metrics", "revenue", "stock", "writeoff"}
LIVE_DATA_JOB_CONFIGS = {
    "tracking": {
        "job_name": "tracking_job",
        "op_name": "tracking_op",
        "success_popup": "Starting tracking collection...",
        "error_popup": "Unable to start tracking",
    },
    "metrics": {
        "job_name": "metrics_manual_job",
        "op_name": "metrics_manual_op",
        "success_popup": "Starting metrics collection...",
        "error_popup": "Unable to start metrics report",
    },
    "revenue": {
        "job_name": "revenue_manual_job",
        "op_name": "revenue_manual_op",
        "success_popup": "Starting revenue collection...",
        "error_popup": "Unable to start revenue report",
    },
    "stock": {
        "job_name": "stock_manual_job",
        "op_name": "stock_manual_op",
        "success_popup": "Starting stock balance collection...",
        "error_popup": "Unable to start stock balance report",
    },
}


def _main_menu_text(_: Callable[[str], str]) -> str:
    """Текст-заголовок главного меню."""
    return _("Choose an action:")


def _section_title(_: Callable[[str], str], section: str) -> str:
    """Возвращает заголовок для экрана выбранного раздела."""
    if section == "notifications":
        return _(MenuTexts.NOTIFICATIONS_TITLE)
    if section == "stops":
        return _(MenuTexts.STOPS_TITLE)
    if section == "reports":
        return _(MenuTexts.REPORTS_TITLE)
    return _(MenuTexts.LIVE_DATA_TITLE)


def _section_keyboard(_: Callable[[str], str], section: str):
    """Возвращает клавиатуру второго уровня."""
    if section == "notifications":
        return notifications_menu_keyboard(_)
    if section == "stops":
        return stops_menu_keyboard(_)
    if section == "reports":
        return reports_menu_keyboard(_)
    return live_data_menu_keyboard(_)


def _no_locations_message(_: Callable[[str], str], user_ctx: dict[str, object] | None) -> str:
    """Подсказывает причину, почему нельзя открыть выбор заведений."""
    if not user_ctx or not user_ctx.get("accounts"):
        return _(MenuTexts.NO_LINKED_ACCOUNTS)
    return _(MenuTexts.NO_AVAILABLE_LOCATIONS)


def _live_data_title(_: Callable[[str], str], operation: str) -> str:
    """Заголовок выбора заведений для конкретного live-data отчета."""
    mapping = {
        "tracking": "Choose locations for tracking:",
        "metrics": "Choose locations for metrics:",
        "revenue": "Choose locations for network revenue:",
        "stock": "Choose locations for stock balances:",
    }
    return _(mapping.get(operation, "Choose locations:"))


def _available_units(user_ctx: dict[str, object] | None) -> list[dict[str, str]]:
    """Уникальные и отсортированные заведения из пользовательского контекста."""
    unique: dict[str, dict[str, str]] = {}
    for unit in (user_ctx or {}).get("units", []):
        if not isinstance(unit, dict):
            continue
        unit_uuid = str(unit.get("uuid") or "").strip()
        unit_name = str(unit.get("name") or unit_uuid).strip() or unit_uuid
        if not unit_uuid:
            continue
        unique.setdefault(unit_uuid, {"uuid": unit_uuid, "name": unit_name})
    return sorted(unique.values(), key=lambda item: item["name"].lower())


def _units_meta(user_ctx: dict[str, object] | None) -> dict[str, dict[str, object]]:
    """Метаданные доступных заведений пользователя по uuid."""
    meta: dict[str, dict[str, object]] = {}
    for unit in (user_ctx or {}).get("units", []):
        if not isinstance(unit, dict):
            continue
        unit_uuid = str(unit.get("uuid") or "").strip()
        if not unit_uuid:
            continue
        meta.setdefault(
            unit_uuid,
            {
                "name": str(unit.get("name") or unit_uuid).strip() or unit_uuid,
                "account_id": unit.get("account_id"),
            },
        )
    return meta


def _subscription_title(_: Callable[[str], str], post: str) -> str:
    """Заголовок выбора заведений для любого post подписки."""
    label = POST.get(post, post)
    return f"{_(MenuTexts.CHOOSE_REPORT_LOCATIONS)}\n{_(label)}"


def _selected_unit_names(selected: set[str], user_ctx: dict[str, object] | None) -> list[str]:
    """Возвращает отсортированные названия выбранных заведений."""
    meta = _units_meta(user_ctx)
    names = [str(meta.get(unit_uuid, {}).get("name") or unit_uuid) for unit_uuid in selected]
    return sorted(names, key=str.lower)


def _subscription_result_text(
    _: Callable[[str], str],
    *,
    post: str,
    selected: set[str],
    user_ctx: dict[str, object] | None,
) -> str:
    """Собирает итоговый текст после сохранения подписок."""
    label = _(POST.get(post, post))
    names = _selected_unit_names(selected, user_ctx)
    if names:
        return (
            _(MenuTexts.APPLY_PREFIX).format(label=label)
            + _(MenuTexts.APPLY_ADDED).format(items="\n".join(names))
        )
    return (
        _(MenuTexts.APPLY_PREFIX).format(label=label)
        + _(MenuTexts.APPLY_NONE)
    )


def _live_data_result_text(
    _: Callable[[str], str],
    *,
    operation: str,
    selected: set[str],
    user_ctx: dict[str, object] | None,
) -> str:
    """Собирает итоговый текст после запуска live-data job."""
    label_map = {
        "tracking": "🛰 Tracking",
        "metrics": "📅 Key metrics",
        "revenue": "💵 Network revenue",
        "stock": "🚚 Large stock balances",
    }
    label = _(label_map.get(operation, operation))
    names = _selected_unit_names(selected, user_ctx)
    if names:
        return _(MenuTexts.LIVE_DATA_STARTED).format(label=label, items="\n".join(names))
    return _(MenuTexts.LIVE_DATA_STARTED_EMPTY).format(label=label)


@router.message_callback(MainMenuPayload.filter())
async def on_main_menu(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: MainMenuPayload,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Обрабатывает простые действия главного меню."""
    action = payload.action

    if action == "settings":
        await facade.edit_message(
            text=_(MenuTexts.SETTINGS_TITLE),
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
            text=_section_title(_, action),
            keyboard=_section_keyboard(_, action),
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
        text=_main_menu_text(_),
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
                text=_section_title(_, target_section),
                keyboard=_section_keyboard(_, target_section),
                format=TextFormat.HTML,
            )
            return
        await facade.edit_message(
            text=_main_menu_text(_),
            keyboard=main_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        return

    if payload.section == "operations" and payload.item in LIVE_DATA_ITEMS:
        units = _available_units(user_ctx)
        if not units:
            await facade.callback_answer(notification=_no_locations_message(_, user_ctx))
            return

        await state.update_data(
            live_operation=payload.item,
            live_selected=[],
        )
        await facade.edit_message(
            text=_live_data_title(_, payload.item),
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
            text=_section_title(_, "stops"),
            keyboard=_section_keyboard(_, "stops"),
            format=TextFormat.HTML,
        )
        return

    if payload.section in {"reports", "notifications", "stops"} and payload.item in (
        REPORT_ITEMS | NOTIFICATION_ITEMS
    ):
        units = _available_units(user_ctx)
        if not units:
            await facade.callback_answer(notification=_no_locations_message(_, user_ctx))
            return

        chat_id = callback.unsafe_message.recipient.chat_id or callback.user.id
        orders = await get_orders_by_post(session, int(chat_id), payload.item, None)
        selected = {unit_uuid for order in orders for unit_uuid in (order.uuids or [])}
        await state.update_data(
            selection_section=payload.section,
            selection_post=payload.item,
            selection_selected=sorted(selected),
            report_post=payload.item,
            report_selected=sorted(selected),
        )
        await facade.edit_message(
            text=_subscription_title(_, payload.item),
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


@router.message_callback(ReportUnitTogglePayload.filter())
async def on_report_unit_toggle(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: ReportUnitTogglePayload,
    state,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Переключает одно заведение в report subscriptions."""
    data = await state.get_data()
    selected = set(data.get("selection_selected") or data.get("report_selected") or [])
    if payload.unit_uuid in selected:
        selected.remove(payload.unit_uuid)
    else:
        selected.add(payload.unit_uuid)

    units = _available_units(user_ctx)
    await state.update_data(
        selection_post=payload.post,
        selection_selected=sorted(selected),
        report_post=payload.post,
        report_selected=sorted(selected),
    )
    await facade.edit_message(
        text=_subscription_title(_, payload.post),
        keyboard=build_report_units_keyboard(
            post=payload.post,
            units=units,
            selected=selected,
            translate=_,
        ),
        format=TextFormat.HTML,
    )


@router.message_callback(ReportUnitsActionPayload.filter())
async def on_report_units_action(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: ReportUnitsActionPayload,
    state,
    session,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Select all / clear / apply / back для report subscriptions."""
    units = _available_units(user_ctx)
    unit_ids = [unit["uuid"] for unit in units]
    data = await state.get_data()
    selected = set(data.get("selection_selected") or data.get("report_selected") or [])
    section = str(data.get("selection_section") or "reports")

    if payload.action == "all":
        selected = set(unit_ids)
    elif payload.action == "clear":
        selected = set()
    elif payload.action == "back":
        await state.update_data(
            selection_section=None,
            selection_post=None,
            selection_selected=[],
            report_post=None,
            report_selected=[],
        )
        await facade.edit_message(
            text=_section_title(_, section),
            keyboard=_section_keyboard(_, section),
            format=TextFormat.HTML,
        )
        return
    elif payload.action == "apply":
        chat_id = int(callback.unsafe_message.recipient.chat_id or callback.user.id)
        orders = await get_orders_by_post(session, chat_id, payload.post, None)

        meta = _units_meta(user_ctx)
        existing_by_account: dict[int | None, set[str]] = {}
        existing_owner_by_uuid: dict[str, int | None] = {}
        for order in orders:
            uuids = set(order.uuids or [])
            existing_by_account.setdefault(order.account_id, set()).update(uuids)
            for unit_uuid in uuids:
                existing_owner_by_uuid.setdefault(unit_uuid, order.account_id)

        accessible_units = set(meta.keys())
        existing_global = set(existing_owner_by_uuid.keys())
        inaccessible_existing = existing_global - accessible_units
        final_global = inaccessible_existing | selected

        final_by_account: dict[int | None, set[str]] = {}
        for unit_uuid in final_global:
            owner_account_id = existing_owner_by_uuid.get(unit_uuid)
            if owner_account_id is None:
                owner_account_id = meta.get(unit_uuid, {}).get("account_id")
            final_by_account.setdefault(owner_account_id if owner_account_id is None else int(owner_account_id), set()).add(unit_uuid)

        accounts = set(existing_by_account.keys()) | set(final_by_account.keys())
        for account_id in accounts:
            final_set = final_by_account.get(account_id, set())
            existing_set = existing_by_account.get(account_id, set())
            if not final_set:
                if existing_set:
                    await delete_order(session, chat_id, payload.post, account_id, None)
                continue
            if final_set != existing_set:
                await upsert_order(
                    session,
                    chat_id,
                    payload.post,
                    account_id,
                    None,
                    sorted(final_set),
                    None,
                )

        await state.update_data(
            selection_section=None,
            selection_post=None,
            selection_selected=[],
            report_post=None,
            report_selected=[],
        )
        await facade.edit_message(
            text=_subscription_result_text(
                _,
                post=payload.post,
                selected=selected,
                user_ctx=user_ctx,
            ),
            keyboard=main_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        popup = MenuTexts.NOTIFICATIONS_UPDATED if section in {"notifications", "stops"} else MenuTexts.REPORTS_UPDATED
        await facade.callback_answer(notification=_(popup))
        return

    await state.update_data(
        selection_section=section,
        selection_post=payload.post,
        selection_selected=sorted(selected),
        report_post=payload.post,
        report_selected=sorted(selected),
    )
    await facade.edit_message(
        text=_subscription_title(_, payload.post),
        keyboard=build_report_units_keyboard(
            post=payload.post,
            units=units,
            selected=selected,
            translate=_,
        ),
        format=TextFormat.HTML,
    )


@router.message_callback(LiveUnitTogglePayload.filter())
async def on_live_unit_toggle(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: LiveUnitTogglePayload,
    state,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Переключает одно заведение в live-data выборе."""
    data = await state.get_data()
    selected = set(data.get("live_selected") or [])
    if payload.unit_uuid in selected:
        selected.remove(payload.unit_uuid)
    else:
        selected.add(payload.unit_uuid)

    units = _available_units(user_ctx)
    await state.update_data(live_operation=payload.operation, live_selected=sorted(selected))
    await facade.edit_message(
        text=_live_data_title(_, payload.operation),
        keyboard=build_live_units_keyboard(
            operation=payload.operation,
            units=units,
            selected=selected,
            translate=_,
        ),
        format=TextFormat.HTML,
    )


@router.message_callback(LiveUnitsActionPayload.filter())
async def on_live_units_action(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: LiveUnitsActionPayload,
    state,
    config,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Обрабатывает select-all / clear / apply / back для live-data выбора."""
    units = _available_units(user_ctx)
    unit_ids = [unit["uuid"] for unit in units]
    data = await state.get_data()
    selected = set(data.get("live_selected") or [])

    if payload.action == "all":
        selected = set(unit_ids)
    elif payload.action == "clear":
        selected = set()
    elif payload.action == "back":
        await state.update_data(live_operation=None, live_selected=[])
        await facade.edit_message(
            text=_section_title(_, "operations"),
            keyboard=live_data_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        return
    elif payload.action == "apply":
        if not selected:
            await facade.callback_answer(notification=tr(_, "Choose at least one location"))
            return

        config_entry = LIVE_DATA_JOB_CONFIGS.get(payload.operation)
        if config_entry is None:
            await facade.callback_answer(notification=tr(_, "Unknown live data report type"))
            return

        from services.dagster import DagsterClient, DagsterLaunchError

        dagster_client = DagsterClient.from_settings(config.dagster)
        op_config = {
            "unit_uuids": sorted(selected),
            "chat_id": int(callback.unsafe_message.recipient.chat_id or callback.user.id),
        }

        try:
            run = await dagster_client.launch_job(
                job_name=config_entry["job_name"],
                op_name=config_entry["op_name"],
                op_config=op_config,
                tags={
                    "source": "aida_max",
                    "post": payload.operation,
                    "action": payload.operation,
                    "chat_id": str(op_config["chat_id"]),
                    "user_id": str(callback.user.id),
                    "unit_count": str(len(selected)),
                },
            )
        except DagsterLaunchError as exc:
            logger.warning("Failed to launch live-data job", action=payload.operation, error=str(exc))
            await facade.callback_answer(notification=tr(_, config_entry["error_popup"]))
            return

        logger.info(
            "Live-data job launched",
            action=payload.operation,
            run_id=run.run_id,
            chat_id=op_config["chat_id"],
            unit_count=len(selected),
        )
        await state.update_data(live_operation=None, live_selected=[])
        await facade.edit_message(
            text=_live_data_result_text(
                _,
                operation=payload.operation,
                selected=selected,
                user_ctx=user_ctx,
            ),
            keyboard=main_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        await facade.callback_answer(notification=tr(_, config_entry["success_popup"]))
        return

    await state.update_data(live_operation=payload.operation, live_selected=sorted(selected))
    await facade.edit_message(
        text=_live_data_title(_, payload.operation),
        keyboard=build_live_units_keyboard(
            operation=payload.operation,
            units=units,
            selected=selected,
            translate=_,
        ),
        format=TextFormat.HTML,
    )


@router.message_callback(LanguagePayload.filter())
async def on_language_selected(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: LanguagePayload,
    session,
    event_from_user,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Сохраняет язык для текущего чата и переоткрывает главное меню на новом языке."""
    chat_id = callback.unsafe_message.recipient.chat_id
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
