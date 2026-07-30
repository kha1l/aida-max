"""Обработчики выбора заведений для подписок и live-data в `aida_max`."""

from __future__ import annotations

from typing import Callable

from loguru import logger
from maxo import Router
from maxo.enums import TextFormat
from maxo.routing.facades import MessageCallbackFacade
from maxo.types import MessageCallback

from bot.callback.live_data import LiveUnitsActionPayload, LiveUnitTogglePayload
from bot.callback.report_selection import ReportUnitsActionPayload, ReportUnitTogglePayload
from bot.keyboards.live_data import build_live_units_keyboard
from bot.keyboards.menu import live_data_menu_keyboard, main_menu_keyboard
from bot.keyboards.report_selection import build_report_units_keyboard
from database.requests.orders import delete_order, get_orders_by_post, upsert_order
from security_logging import pseudonymize
from services.i18n import tr

from .common import (
    LIVE_DATA_JOB_CONFIGS,
    available_units,
    live_data_result_text,
    live_data_title,
    require_callback_chat_id,
    section_keyboard,
    section_title,
    subscription_result_text,
    subscription_title,
    units_meta,
)

router = Router()


@router.message_callback(ReportUnitTogglePayload.filter())
async def on_report_unit_toggle(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: ReportUnitTogglePayload,
    state,
    user_ctx: dict[str, object] | None = None,
    _: Callable[[str], str] = lambda s: s,
) -> None:
    """Переключает одно заведение в выборе подписок."""
    data = await state.get_data()
    selected = set(data.get("selection_selected") or data.get("report_selected") or [])
    if payload.unit_uuid in selected:
        selected.remove(payload.unit_uuid)
    else:
        selected.add(payload.unit_uuid)

    units = available_units(user_ctx)
    await state.update_data(
        selection_post=payload.post,
        selection_selected=sorted(selected),
        report_post=payload.post,
        report_selected=sorted(selected),
    )
    await facade.edit_message(
        text=subscription_title(_, payload.post),
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
    """Обрабатывает select all / clear / apply / back для подписок."""
    units = available_units(user_ctx)
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
            text=section_title(_, section),
            keyboard=section_keyboard(_, section),
            format=TextFormat.HTML,
        )
        return
    elif payload.action == "apply":
        chat_id = require_callback_chat_id(callback)
        orders = await get_orders_by_post(session, chat_id, payload.post, None)

        meta = units_meta(user_ctx)
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
            text=subscription_result_text(
                _,
                post=payload.post,
                selected=selected,
                user_ctx=user_ctx,
            ),
            keyboard=main_menu_keyboard(_),
            format=TextFormat.HTML,
        )
        popup = "Notification subscriptions updated." if section in {"notifications", "stops"} else "Report subscriptions updated."
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
        text=subscription_title(_, payload.post),
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
    """Переключает одно заведение в выборе live-data."""
    data = await state.get_data()
    selected = set(data.get("live_selected") or [])
    if payload.unit_uuid in selected:
        selected.remove(payload.unit_uuid)
    else:
        selected.add(payload.unit_uuid)

    units = available_units(user_ctx)
    await state.update_data(live_operation=payload.operation, live_selected=sorted(selected))
    await facade.edit_message(
        text=live_data_title(_, payload.operation),
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
    """Обрабатывает select all / clear / apply / back для live-data выбора."""
    units = available_units(user_ctx)
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
            text=section_title(_, "operations"),
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
            "chat_id": require_callback_chat_id(callback),
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
            logger.warning(
                "Failed to launch live-data job",
                chat_hash=pseudonymize(op_config["chat_id"]),
                object=f"operation:{payload.operation}",
                error_type=type(exc).__name__,
            )
            await facade.callback_answer(notification=tr(_, config_entry["error_popup"]))
            return

        logger.info(
            "Live-data job launched",
            chat_hash=pseudonymize(op_config["chat_id"]),
            object=f"operation:{payload.operation}",
            request_id=run.run_id,
            status=len(selected),
        )
        await state.update_data(live_operation=None, live_selected=[])
        await facade.edit_message(
            text=live_data_result_text(
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
        text=live_data_title(_, payload.operation),
        keyboard=build_live_units_keyboard(
            operation=payload.operation,
            units=units,
            selected=selected,
            translate=_,
        ),
        format=TextFormat.HTML,
    )
