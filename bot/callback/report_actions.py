"""Payload-объекты для inline-действий отчетов и manual job."""

from maxo.routing.filters import Payload


class ReportActionPayload(Payload, prefix="report"):
    """Действие над отчетом для конкретного заведения."""

    post: str
    action: str
    unit_uuid: str


class WaitingThresholdPayload(Payload, prefix="report_wait"):
    """Порог ожидания курьера в минутах."""

    post: str
    unit_uuid: str
    minutes: int


class DrinkThresholdPayload(Payload, prefix="report_drink"):
    """Порог времени напитка в минутах."""

    post: str
    unit_uuid: str
    minutes: int


class HideReportPayload(Payload, prefix="report_hide"):
    """Удаление сообщения с отчетом."""

    marker: str = "hide"
