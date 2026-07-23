from loguru import logger
from security_logging import loguru_json_sink, redact_record


def setup_logging(
    service_name: str = "aida",
    log_level: str = "INFO",
):
    """Настраивает структурированный вывод логов в stdout."""

    logger.remove()

    def filter_logs(record):
        """Пропускает только записи текущего сервиса."""
        return record["extra"].get("service") == service_name

    logger.add(
        loguru_json_sink,
        level=log_level,
        enqueue=True,
        backtrace=False,
        diagnose=False,
        filter=filter_logs
    )

    logger.configure(extra={"service": service_name}, patcher=redact_record)
