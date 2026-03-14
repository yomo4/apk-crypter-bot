from aiogram import Router, F
from aiogram.types import Message, FSInputFile
import os

from services.apk_crypter import APKCrypter

router = Router()
crypter = APKCrypter()


@router.message(F.document)
async def process_apk_file(message: Message):
    document = message.document
    
    if not document.file_name.endswith('.apk'):
        await message.answer("❌ Это не APK файл. Отправь файл с расширением .apk")
        return
    
    await message.answer("⏳ Шифрую APK и создаю криптованный APK...")
    
    try:
        # Скачиваем файл
        file = await message.bot.get_file(document.file_id)
        file_path = f"temp/{document.file_name}"
        await message.bot.download_file(file.file_path, file_path)
        
        # Криптуем APK
        crypted_apk_path = crypter.create_crypted_apk(file_path)
        
        # Отправляем зашифрованный APK
        crypted_file = FSInputFile(crypted_apk_path)
        await message.answer_document(
            crypted_file,
            caption=f"✅ APK зашифрован!\n\n"
                    f"📁 Оригинал: {document.file_name}\n"
                    f"🔐 Шифрование: AES-256-GCM\n"
                    f"📦 Stub собран автоматически\n"
                    f"✨ Готов к установке"
        )
        os.remove(file_path)
        os.remove(crypted_apk_path)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при шифровании: {str(e)}")
