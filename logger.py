import sys
from loguru import logger


def setup_logging(
    service_name: str = "aida",
    log_level: str = "INFO",
):
    """Настраивает вывод логов в stdout и файл сервиса."""

    logger.remove()

    def filter_logs(record):
        """Пропускает только записи текущего сервиса."""
        return record["extra"].get("service") == service_name

    logger.add(
        sys.stdout,
        serialize=True,
        level=log_level,
        enqueue=True,
        backtrace=True,
        filter=filter_logs
    )

    logger.add(
        f"logs/{service_name}.log",
        serialize=True,
        rotation="10 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
        backtrace=True,
        filter=filter_logs,
    )

    logger.configure(extra={"service": service_name})
