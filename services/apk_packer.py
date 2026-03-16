import hashlib
import logging
import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


class APKPacker:
    def __init__(self):
        self.temp_dir = Path("temp/packer")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("APKPacker initialized")

    @staticmethod
    def _sha256_keystream(key: bytes, length: int) -> bytes:
        """
        Генерирует keystream заданной длины на основе SHA-256.
        keystream = SHA256(key||0) + SHA256(key||1) + ...
        """
        stream = bytearray()
        counter = 0
        while len(stream) < length:
            block = hashlib.sha256(key + counter.to_bytes(4, "big")).digest()
            stream.extend(block)
            counter += 1
        return bytes(stream[:length])

    def pack_apk(self, payload_apk_path: str) -> Tuple[str, str]:
        """
        Шифрует APK через XOR с SHA-256 keystream.

        Формат зашифрованного файла:
          [32 bytes] случайный ключ (plain)
          [N bytes]  XOR(apk_data, SHA256_keystream(key))

        Returns:
            (путь к зашифрованному файлу, hex-ключ для расшифровки)
        """
        apk_path = Path(payload_apk_path)
        logger.info(f"Packing APK: {apk_path}")

        apk_data = apk_path.read_bytes()
        original_sha256 = hashlib.sha256(apk_data).hexdigest()
        logger.info(f"SHA-256 оригинала: {original_sha256}")

        # Генерируем случайный 32-байтовый ключ
        key = secrets.token_bytes(32)
        key_hex = key.hex()

        # Шифруем XOR с SHA-256 keystream
        keystream = self._sha256_keystream(key, len(apk_data))
        encrypted = bytes(a ^ b for a, b in zip(apk_data, keystream))

        output_name = f"{apk_path.stem}_packed_{datetime.now():%Y%m%d_%H%M%S}.apk"
        final_apk = self.output_dir / output_name

        with open(final_apk, "wb") as f:
            f.write(key)        # 32 байта ключ
            f.write(encrypted)  # зашифрованный APK

        size_kb = final_apk.stat().st_size // 1024
        logger.info(f"Output APK: {final_apk.name} ({size_kb} KB) | key={key_hex[:16]}...")

        return str(final_apk), key_hex
