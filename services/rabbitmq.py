"""Фоновый consumer RabbitMQ для доставки готовых payload в MAX."""

from __future__ import annotations

import asyncio
import contextlib
import json
from dataclasses import dataclass

import aio_pika
from loguru import logger
from maxo import Bot
from maxo.enums import TextFormat
from maxo.errors import MaxBotBadRequestError, MaxBotForbiddenError, MaxBotNotFoundError
from maxo.types.inline_keyboard_attachment import InlineKeyboardAttachment
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.keyboards.report_actions import POSTS_REQUIRING_UNIT_UUID, build_report_keyboard
from database.requests.orders import delete_orders_for_chat
from database.requests.settings import get_chat_language, get_default_chat_language
from services.i18n import get_translator


@dataclass(slots=True)
class RabbitPayload:
    """Нормализованный payload из очереди для отправки в MAX."""

    chat_id: int
    text: str
    topic_id: int | None
    post: str | None
    unit_uuid: str | None

    @classmethod
    def from_bytes(cls, raw_body: bytes) -> "RabbitPayload":
        """Декодирует JSON из RabbitMQ и приводит его к рабочей структуре."""
        raw_payload = json.loads(raw_body.decode())
        return cls(
            chat_id=int(raw_payload["chat_id"]),
            text=raw_payload["text"],
            topic_id=raw_payload.get("topic_id"),
            post=raw_payload.get("post"),
            unit_uuid=raw_payload.get("unit_uuid") or raw_payload.get("uuid"),
        )


async def _resolve_chat_translator(
    session_maker: async_sessionmaker[AsyncSession] | None,
    chat_id: int,
):
    """Подбирает переводчик для чата по языку, сохраненному в БД."""
    if session_maker is None:
        return lambda message: message

    try:
        async with session_maker() as session:
            language = await get_chat_language(session, chat_id)
            if not language:
                language = await get_default_chat_language(session, chat_id)
    except SQLAlchemyError as exc:
        logger.warning(
            "Не удалось загрузить язык чата для RabbitMQ-доставки, используем ru по умолчанию",
            chat_id=chat_id,
            error=str(exc),
        )
        language = "ru"
    return get_translator(language=language or "ru")


def _build_keyboard_attachments(post: str | None, unit_uuid: str | None, translate):
    """Преобразует inline-клавиатуру в attachments MAX."""
    keyboard = build_report_keyboard(post, unit_uuid, translate=translate)
    if not keyboard:
        return None
    return [InlineKeyboardAttachment.factory(buttons=keyboard)]


def _is_unavailable_max_dialog_error(
    exc: MaxBotBadRequestError | MaxBotForbiddenError | MaxBotNotFoundError,
) -> bool:
    """Проверяет, что MAX delivery error означает постоянную недоступность диалога."""
    text = f"{exc.code} {exc.error} {exc.message}".lower()
    expected_fragments = (
        "chat.denied",
        "dialog.suspended",
        "dialog.not.found",
        "chat not found",
        "dialog not found",
    )
    return any(fragment in text for fragment in expected_fragments)


async def _delete_delivery_subscriptions(
    session_maker: async_sessionmaker[AsyncSession] | None,
    *,
    payload: RabbitPayload,
) -> int:
    if session_maker is None:
        return 0
    try:
        async with session_maker() as session:
            return await delete_orders_for_chat(session, payload.chat_id)
    except SQLAlchemyError as exc:
        logger.bind(
            chat_id=payload.chat_id,
            topic_id=payload.topic_id,
            post=payload.post,
            unit_uuid=payload.unit_uuid,
            error=str(exc),
        ).warning("Delivery cleanup skipped: failed to delete subscriptions")
        return 0


async def rabbit_listener(
    bot: Bot,
    rabbit_url: str,
    queue_name: str,
    session_maker: async_sessionmaker[AsyncSession] | None = None,
) -> None:
    """Слушает очередь RabbitMQ и пересылает сообщения в MAX."""
    connection = None
    channel = None
    queue = None
    consumer_tag = None

    async def on_message(message: aio_pika.IncomingMessage) -> None:
        payload: RabbitPayload | None = None
        async with message.process():
            try:
                payload = RabbitPayload.from_bytes(message.body)
                translate = await _resolve_chat_translator(session_maker, payload.chat_id)
                attachments = _build_keyboard_attachments(payload.post, payload.unit_uuid, translate)

                if payload.post in POSTS_REQUIRING_UNIT_UUID and not payload.unit_uuid:
                    logger.bind(
                        chat_id=payload.chat_id,
                        topic_id=payload.topic_id,
                        queue=queue_name,
                        post=payload.post,
                    ).warning("Keyboard skipped: unit_uuid is missing in payload")

                if payload.topic_id is not None:
                    logger.bind(
                        chat_id=payload.chat_id,
                        topic_id=payload.topic_id,
                        queue=queue_name,
                        post=payload.post,
                    ).info("topic_id is ignored in aida_max/MAX delivery")

                await bot.send_message(
                    chat_id=payload.chat_id,
                    text=payload.text,
                    format=TextFormat.HTML,
                    attachments=attachments,
                )

                logger.bind(
                    chat_id=payload.chat_id,
                    topic_id=payload.topic_id,
                    queue=queue_name,
                    post=payload.post,
                    unit_uuid=payload.unit_uuid,
                ).info("Message delivered")

            except (MaxBotBadRequestError, MaxBotForbiddenError, MaxBotNotFoundError) as exc:
                if payload is not None and _is_unavailable_max_dialog_error(exc):
                    deleted = await _delete_delivery_subscriptions(
                        session_maker,
                        payload=payload,
                    )
                    logger.bind(
                        chat_id=payload.chat_id,
                        topic_id=payload.topic_id,
                        queue=queue_name,
                        post=payload.post,
                        unit_uuid=payload.unit_uuid,
                        deleted=deleted,
                        reason=exc.__class__.__name__,
                    ).info("MAX dialog unavailable; subscriptions removed")
                else:
                    logger.bind(
                        chat_id=payload.chat_id if payload else None,
                        topic_id=payload.topic_id if payload else None,
                        queue=queue_name,
                        post=payload.post if payload else None,
                        unit_uuid=payload.unit_uuid if payload else None,
                    ).exception("Failed to send message from RabbitMQ")

            except Exception:
                logger.bind(
                    chat_id=payload.chat_id if payload else None,
                    topic_id=payload.topic_id if payload else None,
                    queue=queue_name,
                    post=payload.post if payload else None,
                    unit_uuid=payload.unit_uuid if payload else None,
                ).exception("Failed to send message from RabbitMQ")

    try:
        await bot.start()
        connection = await aio_pika.connect_robust(rabbit_url)
        channel = await connection.channel()
        await channel.set_qos(prefetch_count=15)
        queue = await channel.declare_queue(queue_name, durable=True)
        consumer_tag = await queue.consume(on_message)

        logger.bind(queue=queue_name).info("Rabbit listener started")
        await asyncio.Future()
    except asyncio.CancelledError:
        logger.bind(queue=queue_name).info("Rabbit listener stopped")
        raise
    finally:
        if queue is not None and consumer_tag is not None:
            with contextlib.suppress(Exception):
                await queue.cancel(consumer_tag)
        if channel is not None:
            with contextlib.suppress(Exception):
                await channel.close()
        if connection is not None:
            with contextlib.suppress(Exception):
                await connection.close()
