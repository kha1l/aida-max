"""Клавиатуры простого меню для первого UI на `maxo`."""

from __future__ import annotations

from collections.abc import Callable

from maxo.utils.builders import KeyboardBuilder

from bot.callback.menu import LanguagePayload, MainMenuPayload, SectionPayload, SettingsPayload


Translator = Callable[[str], str]


def main_menu_keyboard(_: Translator):
    """Возвращает главное меню с минимальным набором действий."""
    return (
        KeyboardBuilder()
        .add_callback(_("🔊 Notifications"), MainMenuPayload(action="notifications").pack())
        .add_callback(_("📑 Reports"), MainMenuPayload(action="reports").pack())
        .add_callback(_("💬 Live data"), MainMenuPayload(action="operations").pack())
        .add_callback(_("🛠 Settings"), MainMenuPayload(action="settings").pack())
        .add_callback(_("❎ Close menu"), MainMenuPayload(action="close").pack())
        .adjust(1, repeat=True)
        .build()
    )


def settings_menu_keyboard(_: Translator):
    """Возвращает экран настроек приложения."""
    return (
        KeyboardBuilder()
        .add_link(_("📱 Manage app"), "https://marketplace.dodois.io/apps/11ECF3AAF97D059CB9706F21406EBD11")
        .add_link(_("📚 Knowledge base"), "https://aida.kaiten.site")
        .add_callback(_("🌐 Change language"), SettingsPayload(action="language").pack())
        .add_callback(_("🔙 Back"), SettingsPayload(action="back").pack())
        .adjust(1, repeat=True)
        .build()
    )


def language_menu_keyboard(_: Translator):
    """Возвращает экран выбора языка."""
    return (
        KeyboardBuilder()
        .add_callback(_("🇷🇺 Russian"), LanguagePayload(code="ru").pack())
        .add_callback(_("🇬🇧 English"), LanguagePayload(code="en").pack())
        .add_callback(_("🔙 Back"), SettingsPayload(action="back").pack())
        .adjust(1, repeat=True)
        .build()
    )


def _section_keyboard(_: Translator, *, section: str, items: list[tuple[str, str]]):
    """Базовый builder для простых меню второго уровня."""
    builder = KeyboardBuilder()
    for text, item in items:
        builder.add_callback(_(text), SectionPayload(section=section, item=item).pack())
    builder.add_callback(_("🔙 Back"), SectionPayload(section=section, item="back").pack())
    return builder.adjust(1, repeat=True).build()


def notifications_menu_keyboard(_: Translator):
    """Раздел уведомлений."""
    return _section_keyboard(
        _,
        section="notifications",
        items=[
            ("🎉 Birthdays", "birthday"),
            ("🛑 Stops", "stops"),
            ("📘 Customer tickets", "tickets"),
            ("🧾 Staff info", "staff"),
            ("🅾 Cancelled orders", "refusal"),
            ("🧪 Defect", "defect"),
        ],
    )


def stops_menu_keyboard(_: Translator):
    """Подменю типов стопов."""
    return _section_keyboard(
        _,
        section="stops",
        items=[
            ("🏢 Stops by sales channels", "stops_rest"),
            ("🍕 Stops by key ingredients", "stops_key_ings"),
            ("🧀 Stops by ingredients", "stops_ings"),
            ("🗾 Stops by sectors", "stops_sector"),
        ],
    )


def reports_menu_keyboard(_: Translator):
    """Раздел отчетов."""
    return _section_keyboard(
        _,
        section="reports",
        items=[
            ("🚛 Courier reports", "couriers"),
            ("🍳 Restaurant reports", "stationary"),
            ("📅 Key metrics", "metrics"),
            ("📈 Ratings RKO/RS", "ratings"),
            ("💵 Network revenue", "revenue"),
            ("🚚 Stock balances", "stock"),
            ("🗑 Write-offs", "writeoff"),
        ],
    )


def live_data_menu_keyboard(_: Translator):
    """Раздел оперативных данных."""
    return _section_keyboard(
        _,
        section="operations",
        items=[
            ("📊 Current metrics", "metrics"),
            ("💵 Network revenue", "revenue"),
            ("🚚 Stock balances", "stock"),
            ("🛰 Tracking", "tracking"),
        ],
    )
