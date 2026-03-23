"""CRUD-запросы к таблице `aida.orders`."""
from typing import Iterable, List

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Orders
from loguru import logger


async def get_orders_by_post(
    session: AsyncSession,
    chat_id: int,
    post: str,
    topic_id: int | None = None,
) -> List[Orders]:
    """Получает подписки по типу отчёта (post) и чату."""
    stmt = select(Orders).where(Orders.chat_id == chat_id, Orders.post == post)
    stmt = stmt.where(Orders.topic_id == topic_id) if topic_id is not None else stmt.where(Orders.topic_id.is_(None))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def upsert_order(
    session: AsyncSession,
    chat_id: int,
    post: str,
    account_id: int | None,
    topic_id: int | None,
    uuids: list[str],
    params: str | None = None,
) -> None:
    """Создаёт или обновляет подписку на отчёт для аккаунта."""
    stmt = select(Orders.id).where(Orders.chat_id == chat_id, Orders.post == post, Orders.account_id == account_id)
    stmt = stmt.where(Orders.topic_id == topic_id) if topic_id is not None else stmt.where(Orders.topic_id.is_(None))
    result = await session.execute(stmt)
    order_id = result.scalar_one_or_none()

    if order_id:
        upd = (
            update(Orders)
            .where(Orders.id == order_id)
            .values(uuids=uuids, params=params, topic_id=topic_id)
        )
        await session.execute(upd)
    else:
        session.add(
            Orders(
                chat_id=chat_id,
                post=post,
                account_id=account_id,
                topic_id=topic_id,
                uuids=uuids,
                params=params,
            )
        )
    await session.commit()
    logger.info(
        "orders upsert",
        post=post,
        chat_id=chat_id,
        account_id=account_id,
        topic_id=topic_id,
        uuids=uuids,
        params=params,
    )


async def delete_order(
    session: AsyncSession,
    chat_id: int,
    post: str,
    account_id: int | None,
    topic_id: int | None,
) -> None:
    """Удаляет подписку для указанного аккаунта."""
    stmt = delete(Orders).where(Orders.chat_id == chat_id, Orders.post == post, Orders.account_id == account_id)
    stmt = stmt.where(Orders.topic_id == topic_id) if topic_id is not None else stmt.where(Orders.topic_id.is_(None))
    await session.execute(stmt)
    await session.commit()
    logger.info(
        "orders delete",
        post=post,
        chat_id=chat_id,
        account_id=account_id,
        topic_id=topic_id,
    )
