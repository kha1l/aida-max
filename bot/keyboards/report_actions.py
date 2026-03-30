"""Inline-клавиатуры для отчетов и manual-запусков Dagster jobs на `maxo`."""

from __future__ import annotations

from collections.abc import Callable

from maxo.utils.builders import KeyboardBuilder

from bot.callback.report_actions import (
    DrinkThresholdPayload,
    HideReportPayload,
    ReportActionPayload,
    WaitingThresholdPayload,
)


Translator = Callable[[str], str]
HIDE_ONLY_POSTS = {
    "certificates",
    "later",
    "waiting",
    "sectors",
    "longers",
    "later_rest",
    "assembly_rest",
    "drink_rest",
}
WAITING_THRESHOLD_VALUES_MINUTES = (1, 2, 3, 5, 10)
DRINK_THRESHOLD_VALUES_MINUTES = (1, 2, 3, 4, 5)
COURIERS_REPORT_BUTTONS = (
    ("💤 Courier waiting", "waiting"),
    ("⌚ Late / missed shifts", "later"),
    ("📑 Certificates", "certificates"),
    ("🌏 Sectors", "sectors"),
    ("🛵 Long deliveries", "longers"),
)
STATIONARY_REPORT_BUTTONS = (
    ("📃 Long dine-in orders", "later_rest"),
    ("🧳 Slow order assembly", "assembly_rest"),
    ("🍺 Slow drinks", "drink_rest"),
)


def _hide_row(translate: Translator):
    return [(translate("🔄 Hide report"), HideReportPayload().pack())]


def _with_hide(keyboard: list[list[tuple[str, str]]] | None, translate: Translator):
    rows = keyboard or []
    rows.append(_hide_row(translate))
    return rows


def _rows_to_keyboard(rows: list[list[tuple[str, str]]]):
    """Преобразует пары `(text, payload)` в реальную клавиатуру maxo."""
    builder = KeyboardBuilder()
    from maxo.types.buttons import CallbackButton

    for row in rows:
        builder.row(*[CallbackButton(text=text, payload=payload) for text, payload in row])
    return builder.build()


def _build_action_keyboard(
    *,
    post: str,
    unit_uuid: str,
    buttons: tuple[tuple[str, str], ...],
    translate: Translator,
):
    rows = [
        [
            (
                translate(text),
                ReportActionPayload(post=post, action=action, unit_uuid=unit_uuid).pack(),
            )
        ]
        for text, action in buttons
    ]
    return _rows_to_keyboard(rows)


def _build_threshold_keyboard(
    *,
    post: str,
    unit_uuid: str,
    minutes_values: tuple[int, ...],
    callback_factory,
    translate: Translator,
):
    rows: list[list[tuple[str, str]]] = []
    current_row: list[tuple[str, str]] = []
    for index, minutes in enumerate(minutes_values, start=1):
        current_row.append(
            (
                translate("{minutes} min").format(minutes=minutes),
                callback_factory(post=post, unit_uuid=unit_uuid, minutes=minutes).pack(),
            )
        )
        if index in {3, len(minutes_values)}:
            rows.append(current_row)
            current_row = []
    return _rows_to_keyboard(_with_hide(rows, translate))


def build_waiting_threshold_keyboard(post: str, unit_uuid: str, translate: Translator | None = None):
    translate = translate or (lambda message: message)
    return _build_threshold_keyboard(
        post=post,
        unit_uuid=unit_uuid,
        minutes_values=WAITING_THRESHOLD_VALUES_MINUTES,
        callback_factory=WaitingThresholdPayload,
        translate=translate,
    )


def build_drink_threshold_keyboard(post: str, unit_uuid: str, translate: Translator | None = None):
    translate = translate or (lambda message: message)
    return _build_threshold_keyboard(
        post=post,
        unit_uuid=unit_uuid,
        minutes_values=DRINK_THRESHOLD_VALUES_MINUTES,
        callback_factory=DrinkThresholdPayload,
        translate=translate,
    )


def build_report_keyboard(post: str | None, unit_uuid: str | None, translate: Translator | None = None):
    """Возвращает inline-клавиатуру для отчета из RabbitMQ."""
    translate = translate or (lambda message: message)
    if post in HIDE_ONLY_POSTS:
        return _rows_to_keyboard(_with_hide([], translate))
    if not post or not unit_uuid:
        return None
    if post == "couriers":
        return _build_action_keyboard(
            post=post,
            unit_uuid=unit_uuid,
            buttons=COURIERS_REPORT_BUTTONS,
            translate=translate,
        )
    if post == "stationary":
        return _build_action_keyboard(
            post=post,
            unit_uuid=unit_uuid,
            buttons=STATIONARY_REPORT_BUTTONS,
            translate=translate,
        )
    return None
