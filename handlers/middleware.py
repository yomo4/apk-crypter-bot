"""
Middleware для логирования всех взаимодействий с ботом.
Пишет в лог: user_id, username, тип апдейта, текст/файл, время обработки.
"""

import logging
import time
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import (
    CallbackQuery,
    Document,
    Message,
    TelegramObject,
    Update,
)

logger = logging.getLogger("bot.middleware")


def _user_tag(message: Message) -> str:
    """Формирует строку-идентификатор пользователя"""
    user = message.from_user
    if not user:
        return "unknown"
    name = user.full_name or ""
    username = f"@{user.username}" if user.username else "no_username"
    return f"[{user.id} | {username} | {name}]"


def _describe_message(message: Message) -> str:
    """Описывает содержимое сообщения"""
    if message.text:
        short = message.text[:80].replace("\n", " ")
        return f"text: «{short}»"
    if message.document:
        doc: Document = message.document
        return f"document: {doc.file_name} ({doc.file_size} bytes, mime={doc.mime_type})"
    if message.photo:
        return f"photo ({len(message.photo)} sizes)"
    if message.sticker:
        return f"sticker: {message.sticker.emoji}"
    if message.voice:
        return f"voice ({message.voice.duration}s)"
    if message.video:
        return f"video ({message.video.duration}s)"
    return f"type={message.content_type}"


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware логирует каждый апдейт:
      - кто отправил (user_id, username)
      - что отправил (текст, файл и т.д.)
      - сколько времени заняла обработка
      - ошибки если есть
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        start = time.monotonic()

        # Определяем что за апдейт
        if isinstance(event, Message):
            user_tag = _user_tag(event)
            description = _describe_message(event)
            chat_id = event.chat.id
            logger.info(
                "→ MESSAGE | chat=%s | user=%s | %s",
                chat_id, user_tag, description,
            )
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            user_tag = f"[{user.id} | @{user.username or 'no_username'}]"
            logger.info(
                "→ CALLBACK | user=%s | data=%s",
                user_tag, event.data,
            )
        else:
            # Прочие апдейты (inline, poll, etc.) — только тип
            logger.debug("→ EVENT type=%s", type(event).__name__)

        try:
            result = await handler(event, data)

            elapsed = (time.monotonic() - start) * 1000
            if isinstance(event, (Message, CallbackQuery)):
                logger.info("✓ DONE | user=%s | %.1f ms", user_tag, elapsed)

            return result

        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            if isinstance(event, (Message, CallbackQuery)):
                logger.error(
                    "✗ ERROR | user=%s | %.1f ms | %s: %s",
                    user_tag, elapsed, type(exc).__name__, exc,
                    exc_info=True,
                )
            raise
