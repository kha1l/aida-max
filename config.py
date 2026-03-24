"""Конфигурация `aida_max`, собираемая из переменных окружения."""

from dataclasses import dataclass
from environs import Env


@dataclass
class Bot:
    """Настройки MAX-бота."""
    token: str


@dataclass
class Database:
    """Параметры подключения к PostgreSQL."""
    name: str
    user: str
    password: str
    host: str


@dataclass
class Redis:
    """Параметры подключения к Redis."""
    host: str
    port: int


@dataclass
class Rabbit:
    """Параметры подключения к RabbitMQ."""
    url: str
    queue: str


@dataclass
class MaxAuth:
    """Параметры внешнего MAX auth/bind flow."""
    bind_url: str | None
    request_timeout_seconds: int


@dataclass
class Dagster:
    """Параметры запуска Dagster job через GraphQL."""
    graphql_url: str | None
    repository_location_name: str | None
    repository_name: str
    auth_header_name: str | None
    auth_header_value: str | None
    request_timeout_seconds: int


@dataclass
class Config:
    """Корневая конфигурация приложения."""
    bot: Bot
    dbase: Database
    redis: Redis
    rabbit: Rabbit
    max_auth: MaxAuth
    dagster: Dagster


def load_config(path: str | None = None) -> Config:
    """Собирает конфигурацию приложения из переменных окружения."""
    env = Env()
    env.read_env(path)
    return Config(
        bot=Bot(token=env.str("TOKEN")),
        dbase=Database(
            name=env.str("DBASE_NAME"),
            user=env.str("DBASE_USER"),
            password=env.str("DBASE_PASSWORD"),
            host=env.str("DBASE_HOST"),
        ),
        redis=Redis(
            host=env.str("REDIS_HOST"),
            port=env.int("REDIS_PORT"),
        ),
        rabbit=Rabbit(
            url=env.str("RABBIT_URL"),
            queue=env.str("RABBIT_QUEUE", "aida_max"),
        ),
        max_auth=MaxAuth(
            bind_url=env.str("MAX_BIND_URL", "").strip() or None,
            request_timeout_seconds=env.int("MAX_BIND_REQUEST_TIMEOUT_SECONDS", 15),
        ),
        dagster=Dagster(
            graphql_url=env.str("DAGSTER_GRAPHQL_URL", "").strip() or None,
            repository_location_name=env.str("DAGSTER_REPOSITORY_LOCATION", "").strip() or None,
            repository_name=env.str("DAGSTER_REPOSITORY_NAME", "__repository__"),
            auth_header_name=env.str("DAGSTER_AUTH_HEADER_NAME", "").strip() or None,
            auth_header_value=env.str("DAGSTER_AUTH_HEADER_VALUE", "").strip() or None,
            request_timeout_seconds=env.int("DAGSTER_REQUEST_TIMEOUT_SECONDS", 15),
        ),
    )
