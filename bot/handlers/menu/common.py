"""Общие константы и helper-функции для меню `aida_max`."""

from __future__ import annotations

import html
from typing import Callable

from maxo.types import MessageCallback

from bot.dialogs.data import POST
from bot.dialogs.texts import MenuTexts
from bot.helpers.maxo import resolve_callback_chat_id
from bot.keyboards.menu import (
    live_data_menu_keyboard,
    notifications_menu_keyboard,
    reports_menu_keyboard,
    stops_menu_keyboard,
)

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
REPORT_ITEMS = {"couriers", "stationary", "ratings", "metrics", "revenue", "stock", "writeoff"}
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


def require_callback_chat_id(callback: MessageCallback) -> int:
    """Возвращает `chat_id` callback-сообщения с fallback на `user.id`."""
    return resolve_callback_chat_id(callback) or int(callback.user.id)


def main_menu_text(_: Callable[[str], str]) -> str:
    """Текст-заголовок главного меню."""
    return _("Choose an action:")


def settings_text(_: Callable[[str], str], user_ctx: dict[str, object] | None) -> str:
    """Текст экрана настроек со списком аккаунтов пользователя."""
    accounts = []
    for account in (user_ctx or {}).get("accounts", []):
        if not isinstance(account, dict):
            continue
        account_name = str(account.get("name") or "").strip()
        if account_name:
            accounts.append(html.escape(account_name))

    if not accounts:
        return _(MenuTexts.SETTINGS_TITLE)

    account_lines = "\n".join(f"    {name}" for name in accounts)
    return f"{_('Your accounts:')}\n{account_lines}\n{_(MenuTexts.SETTINGS_TITLE)}"


def section_title(_: Callable[[str], str], section: str) -> str:
    """Возвращает заголовок для выбранного раздела меню."""
    if section == "notifications":
        return _(MenuTexts.NOTIFICATIONS_TITLE)
    if section == "stops":
        return _(MenuTexts.STOPS_TITLE)
    if section == "reports":
        return _(MenuTexts.REPORTS_TITLE)
    return _(MenuTexts.LIVE_DATA_TITLE)


def section_keyboard(_: Callable[[str], str], section: str):
    """Возвращает клавиатуру второго уровня для раздела."""
    if section == "notifications":
        return notifications_menu_keyboard(_)
    if section == "stops":
        return stops_menu_keyboard(_)
    if section == "reports":
        return reports_menu_keyboard(_)
    return live_data_menu_keyboard(_)


def no_locations_message(_: Callable[[str], str], user_ctx: dict[str, object] | None) -> str:
    """Подсказывает, почему выбор заведений сейчас недоступен."""
    if not user_ctx or not user_ctx.get("accounts"):
        return _(MenuTexts.NO_LINKED_ACCOUNTS)
    return _(MenuTexts.NO_AVAILABLE_LOCATIONS)


def live_data_title(_: Callable[[str], str], operation: str) -> str:
    """Заголовок экрана выбора заведений для live-data отчета."""
    mapping = {
        "tracking": "Choose locations for tracking:",
        "metrics": "Choose locations for metrics:",
        "revenue": "Choose locations for network revenue:",
        "stock": "Choose locations for stock balances:",
    }
    return _(mapping.get(operation, "Choose locations:"))


def available_units(user_ctx: dict[str, object] | None) -> list[dict[str, str]]:
    """Возвращает уникальный и отсортированный список доступных заведений."""
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


def units_meta(user_ctx: dict[str, object] | None) -> dict[str, dict[str, object]]:
    """Возвращает метаданные доступных заведений по `uuid`."""
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


def subscription_title(_: Callable[[str], str], post: str) -> str:
    """Возвращает заголовок выбора заведений для post-подписки."""
    label = POST.get(post, post)
    return f"{_(MenuTexts.CHOOSE_REPORT_LOCATIONS)}\n{_(label)}"


def selected_unit_names(selected: set[str], user_ctx: dict[str, object] | None) -> list[str]:
    """Возвращает отсортированные названия выбранных заведений."""
    meta = units_meta(user_ctx)
    names = [str(meta.get(unit_uuid, {}).get("name") or unit_uuid) for unit_uuid in selected]
    return sorted(names, key=str.lower)


def subscription_result_text(
    _: Callable[[str], str],
    *,
    post: str,
    selected: set[str],
    user_ctx: dict[str, object] | None,
) -> str:
    """Собирает итоговый текст после сохранения подписок."""
    label = _(POST.get(post, post))
    names = selected_unit_names(selected, user_ctx)
    if names:
        return (
            _(MenuTexts.APPLY_PREFIX).format(label=label)
            + _(MenuTexts.APPLY_ADDED).format(items="\n".join(names))
        )
    return _(MenuTexts.APPLY_PREFIX).format(label=label) + _(MenuTexts.APPLY_NONE)


def live_data_result_text(
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
        "stock": "🚚 Stock balances",
    }
    label = _(label_map.get(operation, operation))
    names = selected_unit_names(selected, user_ctx)
    if names:
        return _(MenuTexts.LIVE_DATA_STARTED).format(label=label, items="\n".join(names))
    return _(MenuTexts.LIVE_DATA_STARTED_EMPTY).format(label=label)
