import logging
import os
import base64
import hashlib
import zipfile
import shutil
import secrets
from pathlib import Path
from typing import Dict, Tuple

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

logger = logging.getLogger(__name__)


class APKCrypter:
    """
    APK Crypter — AES-256-GCM шифрование APK файлов
    """

    def __init__(self):
        self.temp_dir = Path("temp/crypter")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("APKCrypter initialized")

    def _generate_key(self, password: bytes = None, salt: bytes = None) -> Tuple[bytes, bytes]:
        """Генерирует AES-256 ключ из пароля или случайный"""
        if salt is None:
            salt = get_random_bytes(32)
        if password:
            key = hashlib.pbkdf2_hmac("sha256", password, salt, iterations=100_000, dklen=32)
        else:
            key = get_random_bytes(32)
        return key, salt

    def encrypt_bytes(self, data: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
        """Шифрует данные AES-256-GCM. Возвращает (ciphertext, nonce, tag)"""
        nonce = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(data)
        return ciphertext, nonce, tag

    def decrypt_bytes(self, ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
        """Расшифровывает данные AES-256-GCM"""
        cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, tag)

    def create_crypted_apk(self, apk_path: str) -> str:
        """
        Шифрует APK файл с использованием AES-256-GCM.

        Формат зашифрованного файла:
          [4 bytes] magic "CAPK"
          [32 bytes] salt
          [32 bytes] key (зашифрованный, здесь хранится открыто для stub-декриптора)
          [16 bytes] nonce
          [16 bytes] tag
          [4 bytes] original size (big-endian)
          [N bytes] encrypted APK data

        Args:
            apk_path: Путь к исходному APK

        Returns:
            Путь к зашифрованному файлу
        """
        apk_path = Path(apk_path)
        if not apk_path.exists():
            raise FileNotFoundError(f"APK не найден: {apk_path}")

        logger.info(f"Шифрование APK: {apk_path}")

        apk_data = apk_path.read_bytes()
        original_size = len(apk_data)
        logger.info(f"Размер APK: {original_size} байт")

        # Генерация ключа
        key, salt = self._generate_key()

        # Шифрование
        ciphertext, nonce, tag = self.encrypt_bytes(apk_data, key)

        # Формируем зашифрованный файл
        output_name = f"{apk_path.stem}_crypted.apk"
        output_path = self.output_dir / output_name

        with open(output_path, "wb") as f:
            f.write(b"CAPK")                                          # magic
            f.write(salt)                                              # 32 bytes salt
            f.write(key)                                               # 32 bytes key
            f.write(nonce)                                             # 16 bytes nonce
            f.write(tag)                                               # 16 bytes tag
            f.write(original_size.to_bytes(4, "big"))                 # 4 bytes size
            f.write(ciphertext)                                        # encrypted data

        encrypted_size = output_path.stat().st_size
        logger.info(f"Зашифрованный APK: {output_path} ({encrypted_size} байт)")

        return str(output_path)

    def decrypt_apk(self, crypted_path: str, output_path: str = None) -> str:
        """
        Расшифровывает ранее зашифрованный APK.

        Args:
            crypted_path: Путь к зашифрованному APK
            output_path: Путь для сохранения расшифрованного APK

        Returns:
            Путь к расшифрованному APK
        """
        crypted_path = Path(crypted_path)
        if not crypted_path.exists():
            raise FileNotFoundError(f"Зашифрованный APK не найден: {crypted_path}")

        with open(crypted_path, "rb") as f:
            magic = f.read(4)
            if magic != b"CAPK":
                raise ValueError("Неверный формат зашифрованного APK")
            salt = f.read(32)
            key = f.read(32)
            nonce = f.read(16)
            tag = f.read(16)
            original_size = int.from_bytes(f.read(4), "big")
            ciphertext = f.read()

        apk_data = self.decrypt_bytes(ciphertext, key, nonce, tag)
        apk_data = apk_data[:original_size]

        if output_path is None:
            output_path = self.output_dir / f"{crypted_path.stem}_decrypted.apk"
        else:
            output_path = Path(output_path)

        output_path.write_bytes(apk_data)
        logger.info(f"Расшифрованный APK: {output_path}")

        return str(output_path)

    def get_apk_info(self, apk_path: str) -> Dict:
        """Возвращает информацию о APK файле"""
        apk_path = Path(apk_path)
        if not apk_path.exists():
            return {"error": "Файл не найден"}

        info = {
            "name": apk_path.name,
            "size": apk_path.stat().st_size,
            "sha256": hashlib.sha256(apk_path.read_bytes()).hexdigest(),
        }

        try:
            with zipfile.ZipFile(apk_path, "r") as z:
                info["files_count"] = len(z.namelist())
                info["is_valid_apk"] = "AndroidManifest.xml" in z.namelist()
        except Exception:
            info["is_valid_apk"] = False

        return info
