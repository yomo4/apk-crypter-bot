from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import os


class CryptoHandler:
    def __init__(self, key: str):
        """Инициализация с ключом шифрования"""
        self.key = self._derive_key(key)
        self.aesgcm = AESGCM(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Генерация 256-битного ключа из пароля"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'telegram_bot_salt',
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def decrypt_file(self, file_data: bytes, skip_bytes: int = 256) -> bytes:
        """
        Расшифровка файла по аналогии с Java кодом:
        1. Пропускаем первые skip_bytes байт (мусор)
        2. Читаем 12 байт nonce
        3. Расшифровываем остальное через AES-GCM
        """
        try:
            # Пропускаем мусор
            data = file_data[skip_bytes:]
            
            # Извлекаем nonce (12 байт)
            nonce = data[:12]
            
            # Зашифрованные данные
            encrypted_data = data[12:]
            
            # Расшифровываем
            decrypted = self.aesgcm.decrypt(nonce, encrypted_data, None)
            
            return decrypted
        except Exception as e:
            raise ValueError(f"Ошибка расшифровки: {str(e)}")
    
    def encrypt_file(self, file_data: bytes, add_garbage: bool = True) -> bytes:
        """
        Шифрование файла:
        1. Добавляем 256 байт мусора в начало (опционально)
        2. Генерируем nonce (12 байт)
        3. Шифруем данные через AES-GCM
        """
        try:
            # Генерируем nonce
            nonce = os.urandom(12)
            
            # Шифруем данные
            encrypted = self.aesgcm.encrypt(nonce, file_data, None)
            
            # Собираем результат
            result = bytearray()
            
            if add_garbage:
                # Добавляем 256 байт мусора
                result.extend(os.urandom(256))
            
            # Добавляем nonce и зашифрованные данные
            result.extend(nonce)
            result.extend(encrypted)
            
            return bytes(result)
        except Exception as e:
            raise ValueError(f"Ошибка шифрования: {str(e)}")
