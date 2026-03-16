import hashlib
import logging
import os
import time

from aiogram import Router, F
from aiogram.types import Message, FSInputFile

from services.apk_packer import APKPacker

router = Router()
packer = APKPacker()
logger = logging.getLogger(__name__)


def _user_info(message: Message) -> str:
    u = message.from_user
    return f"user_id={u.id} username={'@'+u.username if u.username else 'no_username'}"


@router.message(F.document)
async def process_apk_file(message: Message):
    document = message.document
    user_info = _user_info(message)

    if not document.file_name.endswith('.apk'):
        logger.warning(
            "Получен не APK файл | %s | file=%s mime=%s",
            user_info, document.file_name, document.mime_type,
        )
        await message.answer("❌ Это не APK файл. Отправь файл с расширением .apk")
        return

    logger.info(
        "APK получен | %s | file=%s size=%d bytes",
        user_info, document.file_name, document.file_size,
    )
    await message.answer("⏳ Упаковываю APK с обфускацией...")

    start_ts = time.monotonic()

    try:
        # ── Скачиваем файл ────────────────────────────────────────────────────
        logger.info("[1/5] Скачивание | %s | file=%s", user_info, document.file_name)
        os.makedirs("temp", exist_ok=True)
        file = await message.bot.get_file(document.file_id)
        file_path = f"temp/{document.file_name}"
        await message.bot.download_file(file.file_path, file_path)
        dl_size = os.path.getsize(file_path)
        logger.info("[1/5] Скачан | %s | path=%s size=%d bytes", user_info, file_path, dl_size)

        # ── Упаковываем APK ───────────────────────────────────────────────────
        logger.info("[2/5] Упаковка APK | %s", user_info)
        pack_start = time.monotonic()
        packed_apk_path, encryption_key = packer.pack_apk(file_path)
        pack_elapsed = (time.monotonic() - pack_start) * 1000
        logger.info(
            "[2/5] Упакован | %s | output=%s elapsed=%.0f ms",
            user_info, packed_apk_path, pack_elapsed,
        )

        # ── Размер и SHA-256 ──────────────────────────────────────────────────
        logger.info("[3/5] Проверка хеша | %s", user_info)
        packed_size = os.path.getsize(packed_apk_path)
        sha256_hash = hashlib.sha256()
        with open(packed_apk_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        file_hash = sha256_hash.hexdigest()
        orig_kb = document.file_size // 1024
        packed_kb = packed_size // 1024
        logger.info(
            "[3/5] Хеш готов | %s | orig=%d KB packed=%d KB sha256=%s...",
            user_info, orig_kb, packed_kb, file_hash[:16],
        )

        # ── Отправляем результат ──────────────────────────────────────────────
        logger.info("[4/5] Отправка | %s | file=%s", user_info, packed_apk_path)
        packed_file = FSInputFile(packed_apk_path)
        await message.answer_document(
            packed_file,
            caption=(
                f"✅ APK упакован!\n\n"
                f"📁 Оригинал: {document.file_name}\n"
                f"🔐 Обфускация: Включена\n"
                f"🔑 Ключ шифрования (SHA-256):\n<code>{encryption_key}</code>\n"
                f"📦 Размер: {packed_size:,} байт ({packed_kb} KB)\n"
                f"🔐 SHA-256: <code>{file_hash}</code>\n"
                f"✨ Готов к установке"
            ),
        )
        total_ms = (time.monotonic() - start_ts) * 1000
        logger.info(
            "[5/5] Готово | %s | total=%.0f ms",
            user_info, total_ms,
        )

        # ── Чистим временные файлы ────────────────────────────────────────────
        for tmp in (file_path, packed_apk_path):
            try:
                os.remove(tmp)
            except OSError:
                pass
        logger.debug("Временные файлы удалены | %s", user_info)

    except Exception as exc:
        elapsed = (time.monotonic() - start_ts) * 1000
        logger.error(
            "ОШИБКА обработки APK | %s | file=%s elapsed=%.0f ms | %s",
            user_info, document.file_name, elapsed, exc,
            exc_info=True,
        )
        await message.answer(f"❌ Ошибка при упаковке: {exc}")
