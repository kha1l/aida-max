from pathlib import Path
import sys
from typing import Any

if __name__ == "__main__" and __package__ is None:
    # Позволяет запускать файл напрямую без ошибки импорта пакета
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, UserAccount, Account, Token, Subscribe


class PlatformUser:
    """Мини-протокол для объекта пользователя из transport/framework."""

    id: int


async def get_user_id(session: AsyncSession, tg_user: PlatformUser) -> int | None:
    """Возвращает внутренний user_id только для пользователей `platform='max'`."""
    stmt = select(User.id).where(
        User.platform == "max",
        User.platform_id == tg_user.id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_user_context(session: AsyncSession, tg_user: PlatformUser) -> dict[str, Any] | None:
    """Собирает контекст пользователя: аккаунты, свойства и заведения."""
    user_id = await get_user_id(session, tg_user)
    if not user_id:
        return None

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.accounts)
            .selectinload(UserAccount.account)
            .selectinload(Account.tokens)
            .selectinload(Token.subscribes)
            .selectinload(Subscribe.unit),
        )
    )

    result = await session.execute(stmt)
    user: User = result.scalar_one()

    accounts = []
    properties = []
    units = []

    for ua in user.accounts:
        acc = ua.account
        if not acc or not acc.active:
            continue

        accounts.append({
            "id": acc.id,
            "name": acc.name,
        })

        if acc.properties:
            properties.append(acc.properties)

        for token in acc.tokens:
            for sub in token.subscribes:
                if sub.unit:
                    units.append({
                        "uuid": sub.unit.uuid,
                        "name": sub.unit.name,
                        "country": sub.unit.country,
                        "account_id": token.account_id,
                    })

    return {
        "user_id": user.id,
        "accounts": accounts,
        "properties": properties,
        "units": units,
    }
