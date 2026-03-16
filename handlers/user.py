import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    user = message.from_user
    logger.info(
        "/start | user_id=%s | username=%s | full_name=%s",
        user.id,
        f"@{user.username}" if user.username else "no_username",
        user.full_name,
    )
    await message.answer(
        "🔐 APK Crypter Bot\n\n"
        "Отправь APK файл, и я создам stub загрузчик:\n"
        "• Зашифрую APK через AES-256-GCM\n"
        "• Создам stub APK с загрузчиком\n"
        "• Stub расшифрует и установит APK при запуске\n\n"
        "📤 Отправь APK файл"
    )



