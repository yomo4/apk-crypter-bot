from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "🔐 APK Crypter Bot\n\n"
        "Отправь APK файл, и я создам stub загрузчик:\n"
        "• Зашифрую APK через AES-256-GCM\n"
        "• Создам stub APK с загрузчиком\n"
        "• Stub расшифрует и установит APK при запуске\n\n"
        "📤 Отправь APK файл"
    )



