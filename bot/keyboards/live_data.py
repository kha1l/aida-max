"""Клавиатуры выбора заведений для Live data на `maxo`."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from maxo.types.buttons import CallbackButton
from maxo.utils.builders import KeyboardBuilder

from bot.callback.live_data import LiveUnitsActionPayload, LiveUnitTogglePayload


Translator = Callable[[str], str]


def build_live_units_keyboard(
    *,
    operation: str,
    units: Sequence[dict[str, str]],
    selected: set[str],
    translate: Translator,
):
    """Строит клавиатуру выбора заведений для manual live-data job."""
    builder = KeyboardBuilder()

    # Два столбца с заведениями, как и в `aida3`.
    row_buffer: list[CallbackButton] = []
    for unit in units:
        unit_uuid = unit["uuid"]
        unit_name = unit["name"]
        prefix = "✅" if unit_uuid in selected else "☑️"
        row_buffer.append(
            CallbackButton(
                text=f"{prefix} {unit_name}",
                payload=LiveUnitTogglePayload(operation=operation, unit_uuid=unit_uuid).pack(),
            )
        )
        if len(row_buffer) == 2:
            builder.row(*row_buffer)
            row_buffer = []

    if row_buffer:
        builder.row(*row_buffer)

    builder.row(
        CallbackButton(
            text=translate("📌 Select all"),
            payload=LiveUnitsActionPayload(operation=operation, action="all").pack(),
        ),
        CallbackButton(
            text=translate("📌 Clear selection"),
            payload=LiveUnitsActionPayload(operation=operation, action="clear").pack(),
        ),
    )
    builder.row(
        CallbackButton(
            text=translate("👌 Apply"),
            payload=LiveUnitsActionPayload(operation=operation, action="apply").pack(),
        ),
        CallbackButton(
            text=translate("🔙 Back"),
            payload=LiveUnitsActionPayload(operation=operation, action="back").pack(),
        ),
    )
    return builder.build()
