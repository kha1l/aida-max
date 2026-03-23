"""Запросы к пользовательским настройкам чатов."""
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import User, Account, UserAccount, Orders
from database.requests.users import get_user_id
from database.models import Settings
from sqlalchemy import update


class PlatformUser:
    """Мини-протокол для объекта пользователя из transport/framework."""

    id: int


async def get_user_settings(session: AsyncSession, tg_user: PlatformUser) -> list[dict[str, Any]] | None:
    """Возвращает настройки пользователя (включая язык по chat_id)."""
    user_id = await get_user_id(session, tg_user)
    if not user_id:
        return None

    stmt = (
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.settings))
    )

    result = await session.execute(stmt)
    user: User = result.scalar_one()

    settings = []
    for st in user.settings:
        settings.append({
            "id": st.id,
            "country": st.country,
            "users": st.user_id,
            "chat_id": st.chat_id,
        })

    return settings


async def set_chat_language(session: AsyncSession, chat_id: int, country: str) -> None:
    """Backward-compatible wrapper. Используйте set_chat_language_for_user."""
    raise RuntimeError("set_chat_language requires user context; use set_chat_language_for_user")


async def set_chat_language_for_user(
    session: AsyncSession,
    tg_user: PlatformUser,
    chat_id: int,
    country: str,
) -> None:
    """Сохраняет язык для конкретного чата, создавая запись при первом выборе."""
    user_id = await get_user_id(session, tg_user)
    if not user_id:
        return

    existing_stmt = select(Settings.id).where(Settings.chat_id == chat_id).limit(1)
    existing_id = (await session.execute(existing_stmt)).scalar_one_or_none()

    if existing_id is not None:
        stmt = (
            update(Settings)
            .where(Settings.chat_id == chat_id)
            .values(country=country)
        )
        await session.execute(stmt)
    else:
        session.add(
            Settings(
                chat_id=chat_id,
                country=country,
                user_id=user_id,
            )
        )
    await session.commit()


async def get_chat_language(session: AsyncSession, chat_id: int) -> str | None:
    """Возвращает язык интерфейса для конкретного Telegram-чата."""
    stmt = (
        select(Settings.country)
        .where(Settings.chat_id == chat_id)
        .order_by(Settings.id.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_user_language(session: AsyncSession, tg_user: PlatformUser) -> str:
    """Определяет персональный язык пользователя по его доступам, если чат еще не настроен."""
    user_id = await get_user_id(session, tg_user)
    if not user_id:
        return "ru"

    stmt = (
        select(Account.properties)
        .join(UserAccount, UserAccount.account_id == Account.id)
        .where(UserAccount.user_id == user_id, Account.active.is_(True))
    )
    rows = (await session.execute(stmt)).scalars().all()

    for raw in rows:
        properties = str(raw or "").strip().strip("/").lower()
        if not properties:
            continue
        parts = [part for part in properties.split("/") if part]
        if parts and parts[0] == "com":
            return "en"
        if parts and parts[0] == "io":
            return "ru"
        if parts and parts[-1] in {"en", "us", "gb", "com"}:
            return "en"
        if parts and parts[-1] in {"ru", "kz", "by", "uz"}:
            return "ru"

    return "ru"


def _infer_language_from_properties(properties: object) -> str | None:
    """Определяет базовый язык из account.properties (`io/...` -> `ru`, `com/...` -> `en`)."""
    raw = str(properties or "").strip().strip("/").lower()
    if not raw:
        return None

    parts = [part for part in raw.split("/") if part]
    if not parts:
        return None
    if parts[0] == "com" or parts[-1] in {"en", "us", "gb", "com"}:
        return "en"
    if parts[0] == "io" or parts[-1] in {"ru", "kz", "by", "uz"}:
        return "ru"
    return None


async def get_default_chat_language(session: AsyncSession, chat_id: int) -> str:
    """Определяет стартовый язык чата по первому доступному аккаунту из подписок этого чата."""
    stmt = (
        select(Account.properties)
        .join(Orders, Orders.account_id == Account.id)
        .where(Orders.chat_id == chat_id, Account.active.is_(True))
        .order_by(Orders.id.desc())
        .limit(1)
    )
    properties = (await session.execute(stmt)).scalar_one_or_none()
    inferred = _infer_language_from_properties(properties)
    return inferred or "ru"
