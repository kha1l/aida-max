"""Точка входа `aida_max` на базе фреймворка maxo."""

import asyncio
import contextlib

from maxo import Bot, Dispatcher
from maxo.fsm.key_builder import DefaultKeyBuilder
from maxo.fsm.storages.redis import RedisStorage
from maxo.transport.long_polling import LongPolling

from bot.handlers.error_handlers import router as error_router
from bot.handlers.menu_handlers import router as menu_router
from bot.handlers.report_actions import router as report_actions_router
from bot.handlers.start_handlers import router as start_router
from bot.middlewares.mdw_database import DBSessionMiddleware, UserContextMiddleware
from bot.middlewares.mdw_locale import I18nMiddleware
from bot.middlewares.mdw_logging import LoggingMiddleware
from config import Config, load_config
from database.engine import session_maker
from logger import setup_logging
from services.cache import RedisCache
from services.rabbitmq import rabbit_listener


setup_logging("aida_max")


async def main() -> None:
    """Запускает базовый runtime `aida_max` для поэтапной миграции с aiogram."""
    cfg: Config = load_config()
    bot = Bot(cfg.bot.token)

    storage = RedisStorage(
        redis=RedisCache(db=0).get_redis(),
        key_builder=DefaultKeyBuilder(with_destiny=True),
        state_ttl=3600,
        data_ttl=3600,
    )
    dispatcher = Dispatcher(
        storage=storage,
        workflow_data={
            "config": cfg,
            "enrich_update_context": True,
        },
    )

    # Базовые middleware для первого этапа миграции:
    # logging -> db session -> i18n -> user context.
    dispatcher.update.middleware.outer(LoggingMiddleware())
    dispatcher.update.middleware.outer(DBSessionMiddleware(session_maker))
    dispatcher.update.middleware.outer(I18nMiddleware())
    dispatcher.update.middleware.outer(UserContextMiddleware())

    dispatcher.include_router(error_router)
    dispatcher.include_router(start_router)
    dispatcher.include_router(menu_router)
    dispatcher.include_router(report_actions_router)

    rabbit_task = asyncio.create_task(
        rabbit_listener(
            bot=bot,
            rabbit_url=cfg.rabbit.url,
            queue_name=cfg.rabbit.queue,
            session_maker=session_maker,
        ),
        name="rabbit_listener",
    )

    try:
        await LongPolling(dispatcher).start(bot, auto_close_bot=False)
    finally:
        rabbit_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await rabbit_task
        with contextlib.suppress(Exception):
            await storage.close()
        with contextlib.suppress(Exception):
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())
