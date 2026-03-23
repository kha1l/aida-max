"""Клавиатуры выбора заведений для подписок на отчеты."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from maxo.types.buttons import CallbackButton
from maxo.utils.builders import KeyboardBuilder

from bot.callback.report_selection import ReportUnitsActionPayload, ReportUnitTogglePayload


Translator = Callable[[str], str]


def build_report_units_keyboard(
    *,
    post: str,
    units: Sequence[dict[str, str]],
    selected: set[str],
    translate: Translator,
):
    """Строит клавиатуру выбора заведений для report subscriptions."""
    builder = KeyboardBuilder()

    row_buffer: list[CallbackButton] = []
    for unit in units:
        unit_uuid = unit["uuid"]
        unit_name = unit["name"]
        prefix = "✅" if unit_uuid in selected else "☑️"
        row_buffer.append(
            CallbackButton(
                text=f"{prefix} {unit_name}",
                payload=ReportUnitTogglePayload(post=post, unit_uuid=unit_uuid).pack(),
            )
        )
        if len(row_buffer) == 2:
            builder.row(*row_buffer)
            row_buffer = []

    if row_buffer:
        builder.row(*row_buffer)

    builder.row(
        CallbackButton(
            text=translate("📌 Subscribe all"),
            payload=ReportUnitsActionPayload(post=post, action="all").pack(),
        ),
        CallbackButton(
            text=translate("📌 Unsubscribe all"),
            payload=ReportUnitsActionPayload(post=post, action="clear").pack(),
        ),
    )
    builder.row(
        CallbackButton(
            text=translate("👌 Apply"),
            payload=ReportUnitsActionPayload(post=post, action="apply").pack(),
        ),
        CallbackButton(
            text=translate("🔙 Back"),
            payload=ReportUnitsActionPayload(post=post, action="back").pack(),
        ),
    )
    return builder.build()
