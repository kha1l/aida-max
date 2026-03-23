"""Payload-объекты выбора заведений для раздела Reports."""

from maxo.routing.filters import Payload


class ReportUnitTogglePayload(Payload, prefix="report_unit"):
    """Переключение одного заведения для подписки на отчет."""

    post: str
    unit_uuid: str


class ReportUnitsActionPayload(Payload, prefix="report_units"):
    """Действия на экране выбора заведений для подписок на отчеты."""

    post: str
    action: str
