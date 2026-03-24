"""Inline-действия для manual-отчетов на `maxo`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from loguru import logger
from maxo import Router
from maxo.routing.updates import MessageCallback
from maxo.utils.facades import MessageCallbackFacade

from bot.helpers.maxo import resolve_callback_chat_id
from bot.callback.report_actions import (
    DrinkThresholdPayload,
    HideReportPayload,
    ReportActionPayload,
    WaitingThresholdPayload,
)
from bot.keyboards.report_actions import (
    build_drink_threshold_keyboard,
    build_report_keyboard,
    build_waiting_threshold_keyboard,
)
from config import Config, load_config
from services.dagster import DagsterClient, DagsterLaunchError
from services.i18n import tr


router = Router()
DIRECT_REPORT_ACTIONS = {
    "certificates",
    "later",
    "sectors",
    "longers",
    "later_rest",
    "assembly_rest",
}


def _require_callback_chat_id(callback: MessageCallback) -> int:
    """Возвращает `chat_id` диалога, а если его нет — fallback на `user.id`."""
    return resolve_callback_chat_id(callback) or int(getattr(callback.user, "id"))


@dataclass(frozen=True, slots=True)
class ManualReportLaunchConfig:
    job_name: str
    op_name: str
    success_popup: str
    launch_error_popup: str
    log_label: str


MANUAL_REPORT_CONFIGS = {
    "certificates": ManualReportLaunchConfig("certificates_job", "certificates_op", "Starting certificate collection...", "Unable to start certificate report", "Certificates"),
    "later": ManualReportLaunchConfig("later_job", "later_op", "Starting late / missed shift collection...", "Unable to start late / missed shift report", "Later"),
    "waiting": ManualReportLaunchConfig("waiting_job", "waiting_op", "Starting courier waiting collection...", "Unable to start courier waiting report", "Waiting"),
    "sectors": ManualReportLaunchConfig("sectors_job", "sectors_op", "Starting sector report collection...", "Unable to start delivery sectors report", "Sectors"),
    "longers": ManualReportLaunchConfig("longers_job", "longers_op", "Starting long delivery report collection...", "Unable to start long delivery report", "Longers"),
    "later_rest": ManualReportLaunchConfig("later_rest_job", "later_rest_op", "Starting long dine-in order report collection...", "Unable to start long dine-in order report", "LaterRest"),
    "assembly_rest": ManualReportLaunchConfig("assembly_rest_job", "assembly_rest_op", "Starting slow order assembly report collection...", "Unable to start slow order assembly report", "AssemblyRest"),
    "drink_rest": ManualReportLaunchConfig("drink_rest_job", "drink_rest_op", "Starting slow drink report collection...", "Unable to start slow drink report", "DrinkRest"),
}


def _find_unit(user_ctx: dict[str, Any] | None, unit_uuid: str) -> dict[str, Any] | None:
    for unit in (user_ctx or {}).get("units", []):
        if unit.get("uuid") == unit_uuid:
            return unit
    return None


def _build_dagster_client(config: Config) -> DagsterClient:
    return DagsterClient.from_settings(config.dagster)


async def _launch_manual_report(
    facade: MessageCallbackFacade,
    callback: MessageCallback,
    *,
    unit_uuid: str,
    action: str,
    post: str,
    report_config: ManualReportLaunchConfig,
    user_ctx: dict[str, Any] | None,
    extra_op_config: dict[str, Any] | None = None,
    extra_tags: dict[str, str] | None = None,
    config: Config | None = None,
    translate: Callable[[str], str] = lambda message: message,
) -> None:
    unit = _find_unit(user_ctx, unit_uuid)
    if not unit:
        await facade.callback_answer(notification=tr(translate, "Unable to find this location in your access list"))
        return

    account_id = unit.get("account_id")
    if not account_id:
        await facade.callback_answer(notification=tr(translate, "Unable to determine account for this location"))
        return

    config = config or load_config()
    chat_id = _require_callback_chat_id(callback)
    op_config: dict[str, Any] = {
        "unit_uuid": unit_uuid,
        "account_id": int(account_id),
        "chat_id": int(chat_id),
        "message_date": callback.unsafe_message.timestamp.isoformat(),
    }
    if extra_op_config:
        op_config.update(extra_op_config)

    tags = {
        "source": "aida_max",
        "post": post,
        "action": action,
        "unit_uuid": unit_uuid,
        "chat_id": str(op_config["chat_id"]),
        "user_id": str(callback.user.id),
    }
    if extra_tags:
        tags.update(extra_tags)

    client = _build_dagster_client(config)
    try:
        run = await client.launch_job(
            job_name=report_config.job_name,
            op_name=report_config.op_name,
            op_config=op_config,
            tags=tags,
        )
    except DagsterLaunchError as exc:
        logger.bind(unit_uuid=unit_uuid, account_id=account_id, chat_id=op_config["chat_id"], user_id=callback.user.id).warning(
            f"Failed to launch {report_config.log_label.lower()} job",
            error=str(exc),
        )
        await facade.callback_answer(notification=tr(translate, report_config.launch_error_popup))
        return

    logger.bind(
        unit_uuid=unit_uuid,
        unit_name=unit.get("name"),
        account_id=account_id,
        chat_id=op_config["chat_id"],
        user_id=callback.user.id,
        run_id=run.run_id,
        run_status=run.status,
    ).info(f"{report_config.log_label} job launched")
    await facade.callback_answer(notification=tr(translate, report_config.success_popup))


@router.message_callback(ReportActionPayload.filter())
async def on_report_action(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: ReportActionPayload,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda message: message,
) -> None:
    """Обрабатывает inline-кнопки запуска отчетов."""
    if payload.action in DIRECT_REPORT_ACTIONS:
        await _launch_manual_report(
            facade,
            callback,
            unit_uuid=payload.unit_uuid,
            action=payload.action,
            post=payload.post,
            report_config=MANUAL_REPORT_CONFIGS[payload.action],
            user_ctx=user_ctx,
            translate=_,
        )
        return

    if payload.action == "waiting":
        await facade.edit_message(
            keyboard=build_waiting_threshold_keyboard(payload.post, payload.unit_uuid, translate=_),
        )
        await facade.callback_answer(notification=tr(_, "Choose waiting threshold"))
        return

    if payload.action == "drink_rest":
        await facade.edit_message(
            keyboard=build_drink_threshold_keyboard(payload.post, payload.unit_uuid, translate=_),
        )
        await facade.callback_answer(notification=tr(_, "Choose time threshold"))
        return

    await facade.callback_answer(notification=tr(_, "Unable to determine action"))


@router.message_callback(WaitingThresholdPayload.filter())
async def on_waiting_threshold(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: WaitingThresholdPayload,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda message: message,
) -> None:
    await _launch_manual_report(
        facade,
        callback,
        unit_uuid=payload.unit_uuid,
        action="waiting",
        post=payload.post,
        report_config=MANUAL_REPORT_CONFIGS["waiting"],
        user_ctx=user_ctx,
        extra_op_config={"threshold_minutes": payload.minutes},
        extra_tags={"threshold_minutes": str(payload.minutes)},
        translate=_,
    )
    await facade.edit_message(keyboard=build_report_keyboard(payload.post, payload.unit_uuid, translate=_))


@router.message_callback(DrinkThresholdPayload.filter())
async def on_drink_threshold(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    payload: DrinkThresholdPayload,
    user_ctx: dict[str, Any] | None = None,
    _: Callable[[str], str] = lambda message: message,
) -> None:
    await _launch_manual_report(
        facade,
        callback,
        unit_uuid=payload.unit_uuid,
        action="drink_rest",
        post=payload.post,
        report_config=MANUAL_REPORT_CONFIGS["drink_rest"],
        user_ctx=user_ctx,
        extra_op_config={"threshold_minutes": payload.minutes},
        extra_tags={"threshold_minutes": str(payload.minutes)},
        translate=_,
    )
    await facade.edit_message(keyboard=build_report_keyboard(payload.post, payload.unit_uuid, translate=_))


@router.message_callback(HideReportPayload.filter())
async def hide_report(
    callback: MessageCallback,
    facade: MessageCallbackFacade,
    _: Callable[[str], str] = lambda message: message,
) -> None:
    """Удаляет сообщение с отчетом."""
    await facade.delete_message()
    await facade.callback_answer(notification=tr(_, "Hide report"))
