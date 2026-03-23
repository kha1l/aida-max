"""Payload-объекты для выбора заведений в разделе Live data."""

from maxo.routing.filters import Payload


class LiveUnitTogglePayload(Payload, prefix="live_unit"):
    """Переключение одного заведения в списке выбора."""

    operation: str
    unit_uuid: str


class LiveUnitsActionPayload(Payload, prefix="live_units"):
    """Служебные действия на экране выбора заведений."""

    operation: str
    action: str
