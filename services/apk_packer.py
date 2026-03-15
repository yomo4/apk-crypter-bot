import logging
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import hashlib

logger = logging.getLogger(__name__)


class APKPacker:
    """
    APK Packer - встраивает payload APK в основной APK с обфускацией
    Шифрует каждый APK с уникальным SHA-256 ключом
    """
    
    def __init__(self):
        self.temp_dir = Path("temp/packer")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("APKPacker initialized")
    
    def pack_apk(self, payload_apk_path: str) -> tuple[str, str]:
        """
        Упаковывает payload APK с обфускацией и шифрованием
        
        Args:
            payload_apk_path: Путь к оригинальному APK
            
        Returns:
            Кортеж (путь к упакованному APK, SHA-256 ключ шифрования)
        """
        logger.info(f"Packing APK: {payload_apk_path}")
        
        # Создаем рабочую директорию
        work_dir = self.temp_dir / "work"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        
        # Читаем оригинальный APK
        with open(payload_apk_path, 'rb') as f:
            apk_data = f.read()
        
        # Генерируем SHA-256 ключ из содержимого APK
        encryption_key = hashlib.sha256(apk_data).digest()
        encryption_key_hex = encryption_key.hex()
        logger.info(f"Generated encryption key: {encryption_key_hex}")
        
        # Шифруем APK
        encrypted_data = self.encrypt_apk(apk_data, encryption_key)
        logger.info(f"APK encrypted: {len(apk_data)} -> {len(encrypted_data)} bytes")
        
        # Копируем payload в рабочую директорию
        payload_copy = work_dir / "payload.apk"
        with open(payload_copy, 'wb') as f:
            f.write(encrypted_data)
        
        # Распаковываем payload
        payload_dir = work_dir / "payload"
        self.unpack_apk(str(payload_copy), payload_dir)
        
        # Обфусцируем код payload'а
        self.obfuscate_payload(payload_dir)
        
        # Пересобираем payload
        packed_apk = self.repack_apk(payload_dir, Path(payload_apk_path).stem)
        
        logger.info(f"Packed APK ready: {packed_apk}")
        return packed_apk, encryption_key_hex
    
    def encrypt_apk(self, apk_data: bytes, encryption_key: bytes) -> bytes:
        """Шифрует APK с использованием AES-256-GCM"""
        # Генерируем случайный nonce
        nonce = get_random_bytes(12)
        
        # Создаем cipher
        cipher = AES.new(encryption_key, AES.MODE_GCM, nonce=nonce)
        
        # Шифруем данные
        ciphertext, tag = cipher.encrypt_and_digest(apk_data)
        
        # Возвращаем nonce + tag + ciphertext
        return nonce + tag + ciphertext
    
    def unpack_apk(self, apk_path: str, output_dir: Path):
        """Распаковывает APK"""
        with zipfile.ZipFile(apk_path, 'r') as zf:
            zf.extractall(output_dir)
        logger.info(f"Unpacked APK to {output_dir}")
    
    def obfuscate_payload(self, payload_dir: Path):
        """
        Обфусцирует код payload'а
        Переименовывает классы, методы, переменные
        Удаляет отладочную информацию
        """
        logger.info("Obfuscating payload code...")
        
        # Используем ProGuard/R8 для обфускации
        # Это встроено в Android build tools
        
        # Для простоты используем базовую обфускацию:
        # 1. Переименовываем классы в DEX
        # 2. Удаляем строки отладки
        # 3. Минифицируем ресурсы
        
        # TODO: Интегрировать ProGuard/R8
        logger.info("Obfuscation skipped (need ProGuard/R8 integration)")
    
    def repack_apk(self, payload_dir: Path, original_name: str) -> str:
        """Пересобирает APK"""
        output_name = f"{original_name}_packed.apk"
        output_apk = self.output_dir / output_name
        
        # Создаем ZIP
        with zipfile.ZipFile(output_apk, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file_path in payload_dir.rglob('*'):
                if file_path.is_file():
                    arcname = file_path.relative_to(payload_dir)
                    zf.write(file_path, arcname)
        
        logger.info(f"Repacked APK: {output_apk}")
        
        # Подписываем APK
        signed_apk = self.sign_apk(str(output_apk))
        
        return signed_apk
    
    def sign_apk(self, apk_path: str) -> str:
        """Подписывает APK"""
        # TODO: Реализовать подпись
        logger.info(f"APK signing skipped: {apk_path}")
        return apk_path
