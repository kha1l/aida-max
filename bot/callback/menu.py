"""Payload-объекты для простого callback-меню в `aida_max`."""

from maxo.routing.filters import Payload


class MainMenuPayload(Payload, prefix="main"):
    """Действия главного меню."""

    action: str


class SettingsPayload(Payload, prefix="settings"):
    """Действия экрана настроек."""

    action: str


class LanguagePayload(Payload, prefix="lang"):
    """Выбор языка интерфейса."""

    code: str


class SectionPayload(Payload, prefix="section"):
    """Действия внутри разделов главного меню."""

    section: str
    item: str
