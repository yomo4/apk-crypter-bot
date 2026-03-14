import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class CryptoHandler:
    def __init__(self, key: str):
        """Инициализация с ключом шифрования"""
        self.key = self._derive_key(key)
        self.aesgcm = AESGCM(self.key)
    
    @staticmethod
    def _derive_key(password: str, salt: bytes = b'telegram_bot_salt') -> bytes:
        """Генерация 256-битного ключа из пароля"""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    def decrypt_file(self, encrypted_data: bytes, skip_bytes: int = 256) -> bytes:
        """
        Расшифровка файла по алгоритму из Java кода:
        1. Пропускаем первые skip_bytes байт (мусор)
        2. Читаем 12 байт nonce
        3. Расшифровываем остальное через AES-GCM
        """
        try:
            # Пропускаем мусорные байты
            data = encrypted_data[skip_bytes:]
            
            # Извлекаем nonce (12 байт)
            nonce = data[:12]
            
            # Остальное - зашифрованные данные
            ciphertext = data[12:]
            
            # Расшифровываем
            decrypted = self.aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted
            
        except Exception as e:
            raise ValueError(f"Ошибка расшифровки: {e}")
    
    def encrypt_file(self, data: bytes, skip_bytes: int = 256) -> bytes:
        """
        Шифрование файла с добавлением мусорных байт и nonce
        """
        # Генерируем случайный nonce
        nonce = os.urandom(12)
        
        # Шифруем данные
        ciphertext = self.aesgcm.encrypt(nonce, data, None)
        
        # Добавляем мусорные байты в начало
        junk = os.urandom(skip_bytes)
        
        # Собираем: мусор + nonce + зашифрованные данные
        return junk + nonce + ciphertext
