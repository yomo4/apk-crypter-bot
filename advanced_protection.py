import logging
import re
import subprocess
import socket
import os
import sys
from typing import List, Dict, Tuple, Optional
from enum import Enum
from datetime import datetime
import time
import random

logger = logging.getLogger(__name__)


class DetectionType(Enum):
    """Типы обнаружения"""
    DEBUGGER = "debugger"
    EMULATOR = "emulator"
    ROOT = "root"
    FRIDA = "frida"
    XPOSED = "xposed"
    MAGISK = "magisk"
    PROXY = "proxy"
    VPNG = "vpn"


class AndroidEnvironmentDetector:
    """Детектор Android окружения"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.detections: List[Dict] = []

    def detect_debugger(self) -> Tuple[bool, Optional[str]]:
        """Обнаруживает подключенный отладчик"""
        indicators = [
            "android.os.Debug",
            "android.app.ActivityManager",
            "com.android.ddm",
            "gdbserver",
        ]

        try:
            # Проверка через процессы
            if os.path.exists("/proc"):
                with open("/proc/cmdline", "r") as f:
                    cmdline = f.read().lower()
                    if "gdbserver" in cmdline or "debugger" in cmdline:
                        return True, "Обнаружен GDB сервер"

            # Проверка открытых портов отладки
            for port in [5037, 5555]:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result == 0:
                        return True, f"Обнаружен отладчик на порту {port}"
                except:
                    pass

            return False, None

        except Exception as e:
            self.logger.error(f"Ошибка при проверке отладчика: {e}")
            return False, None

    def detect_emulator(self) -> Tuple[bool, List[str]]:
        """Обнаруживает эмулятор"""
        indicators = []

        # Проверка файлов эмулятора
        emulator_files = [
            "/dev/socket/qemud",
            "/dev/qemu_pipe",
            "/system/lib/libc_malloc_debug_qemu.so",
            "/proc/cpuinfo",
            "/system/build.prop",
        ]

        for file_path in emulator_files:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        content = f.read().lower()
                        if any(
                            keyword in content
                            for keyword in ["qemu", "emulator", "virtualbox", "genymotion"]
                        ):
                            indicators.append(f"Обнаружено в {file_path}")
                except:
                    pass

        # Проверка свойств системы
        system_props = Self._get_system_properties()
        suspicious_props = ["goldfish", "ranchu", "qemu"]

        for prop, value in system_props.items():
            if any(keyword in str(value).lower() for keyword in suspicious_props):
                indicators.append(f"Подозрительное свойство {prop}={value}")

        return len(indicators) > 0, indicators

    def detect_root(self) -> Tuple[bool, List[str]]:
        """Обнаруживает root доступ"""
        indicators = []

        # Проверка файлов Su
        su_files = [
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "/data/local/xbin/su",
            "/data/local/su",
            "/system/app/Superuser.apk",
            "/system/app/SuperSU.apk",
        ]

        for su_file in su_files:
            if os.path.exists(su_file):
                indicators.append(f"Обнаружена su бинарник: {su_file}")

        # Проверка Magisk
        magisk_paths = [
            "/sbin/.magisk",
            "/data/adb/magisk",
            "/data/adb/modules",
            "/.magisk",
        ]

        for magisk_path in magisk_paths:
            if os.path.exists(magisk_path):
                indicators.append(f"Обнаружен Magisk: {magisk_path}")

        # Попытка выполнить su команду
        try:
            result = subprocess.run(
                ["su", "-c", "id"],
                capture_output=True,
                timeout=2,
                text=True
            )
            if result.returncode == 0:
                indicators.append("Удалось выполнить su команду")
        except:
            pass

        return len(indicators) > 0, indicators

    def detect_frida(self) -> Tuple[bool, List[str]]:
        """Обнаруживает Frida"""
        indicators = []

        # Проверка Frida портов
        frida_ports = [27042, 27043]
        for port in frida_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result == 0:
                    indicators.append(f"Обнаружен Frida на порту {port}")
            except:
                pass

        # Проверка процессов
        frida_processes = ["frida", "gum-js-loop", "frida-server"]
        try:
            result = subprocess.run(
                ["ps", "-A"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for proc in frida_processes:
                if proc in result.stdout.lower():
                    indicators.append(f"Обнаружен процесс Frida: {proc}")
        except:
            pass

        return len(indicators) > 0, indicators

    def detect_xposed(self) -> Tuple[bool, List[str]]:
        """Обнаруживает Xposed"""
        indicators = []

        xposed_files = [
            "/system/framework/XposedBridge.jar",
            "/system/lib/libxposed_art.so",
            "/system/lib/libxposed.so",
            "/system/lib64/libxposed_art.so",
        ]

        for xposed_file in xposed_files:
            if os.path.exists(xposed_file):
                indicators.append(f"Обнаружен Xposed: {xposed_file}")

        return len(indicators) > 0, indicators

    def detect_magisk(self) -> Tuple[bool, List[str]]:
        """Обнаруживает Magisk"""
        indicators = []

        magisk_files = [
            "/sbin/.magisk",
            "/data/adb/magisk",
            "/data/adb/modules",
            "/.magisk",
            "/data/adb/magisk_merge",
        ]

        for magisk_file in magisk_files:
            if os.path.exists(magisk_file):
                indicators.append(f"Обнаружен Magisk: {magisk_file}")

        return len(indicators) > 0, indicators

    def detect_proxy(self) -> Tuple[bool, Optional[str]]:
        """Обнаруживает прокси"""
        try:
            # Проверка системных переменных прокси
            proxy_vars = ["http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"]
            for var in proxy_vars:
                if var in os.environ:
                    return True, f"Обнаружена переменная прокси: {var}"

            # Проверка портов прокси
            proxy_ports = [8080, 8888, 3128, 9090]
            for port in proxy_ports:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(0.5)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result == 0:
                        return True, f"Обнаружен прокси на порту {port}"
                except:
                    pass

            return False, None

        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении прокси: {e}")
            return False, None

    def detect_vpn(self) -> Tuple[bool, Optional[str]]:
        """Обнаруживает VPN"""
        try:
            # Проверка сетевых интерфейсов
            interfaces_indicators = ["tun", "tap", "pptp"]

            if os.path.exists("/proc/net/route"):
                with open("/proc/net/route", "r") as f:
                    routes = f.read().lower()
                    for indicator in interfaces_indicators:
                        if indicator in routes:
                            return True, f"Обнаружен VPN интерфейс: {indicator}"

            return False, None

        except Exception as e:
            self.logger.error(f"Ошибка при обнаружении VPN: {e}")
            return False, None

    @staticmethod
    def _get_system_properties() -> Dict[str, str]:
        """Получает Android системные свойства"""
        properties = {}
        try:
            result = subprocess.run(
                ["getprop"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.split('\n'):
                match = re.match(r'\[(.*?)\]:\s*\[(.*?)\]', line)
                if match:
                    properties[match.group(1)] = match.group(2)
        except:
            pass

        return properties

    def perform_full_scan(self) -> Tuple[bool, List[Dict]]:
        """Выполняет полную проверку окружения"""
        detections = []

        checks = [
            ("Debugger", self.detect_debugger, False),
            ("Emulator", self.detect_emulator, True),
            ("Root", self.detect_root, True),
            ("Frida", self.detect_frida, True),
            ("Xposed", self.detect_xposed, True),
            ("Magisk", self.detect_magisk, True),
            ("Proxy", self.detect_proxy, False),
            ("VPN", self.detect_vpn, False),
        ]

        for check_name, check_func, is_list_result in checks:
            try:
                result = check_func()
                is_detected = result[0]

                if is_detected:
                    if is_list_result:
                        indicators = result[1]
                    else:
                        indicators = [result[1]] if result[1] else []

                    detection = {
                        "type": check_name,
                        "detected": True,
                        "indicators": indicators,
                        "timestamp": datetime.now()
                    }
                    detections.append(detection)
                    self.logger.warning(
                        f"{check_name} обнаружен: {indicators}")

            except Exception as e:
                self.logger.error(
                    f"Ошибка при проверке {check_name}: {e}")

        return len(detections) == 0, detections

    def get_detection_report(self) -> Dict:
        """Получает отчет об обнаружениях"""
        is_safe, detections = self.perform_full_scan()

        return {
            "is_safe": is_safe,
            "detections_count": len(detections),
            "detections": detections,
            "timestamp": datetime.now(),
            "status": "SAFE" if is_safe else "COMPROMISED"
        }


class AntiAnalysisProtection:
    """Защита от автоматического анализа"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def add_junk_code(self, code: str, junk_count: int = 5) -> str:
        """Добавляет мусорный код"""
        junk_methods = []
        for i in range(junk_count):
            junk = f"""
def junk_method_{i}():
    \"\"\"Мусорный метод для запутывания анализа\"\"\"
    data = {random.randint(1000, 9999)}
    result = data * {random.randint(10, 100)}
    return result
"""
            junk_methods.append(junk)

        return code + '\n'.join(junk_methods) + code

    def add_anti_analysis_checks(self, code: str) -> str:
        """Добавляет проверки анализа"""
        checks = """
# Anti-Analysis Checks
import sys
import os

def check_analysis_tools():
    tools = ['frida', 'strace', 'ltrace', 'gdb', 'radare2', 'ghidra', 'ida']
    for tool in tools:
        if any(tool in path for path in sys.path):
            return False
    return True

if not check_analysis_tools():
    sys.exit(1)
"""
        return checks + '\n' + code

    def obfuscate_flow(self, code: str) -> str:
        """Запутывает управления потока"""
        # Добавляет условия которые всегда верны но выглядят сложными
        obfuscated = """
import random
_random_seed = random.random()
if 1.0 - _random_seed == 0.0 or 1.0 - _random_seed != 0.0:
    pass
"""
        return obfuscated + '\n' + code


class ProtectionDecorator:
    """Декоратор для функций требующих защиты"""

    def __init__(self):
        self.protected_functions = []

    def protect_function(self, func):
        """Декоратор для защиты функций"""
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Добавляем случайную задержку
            delay = random.uniform(0.1, 0.5)
            time.sleep(delay)

            result = func(*args, **kwargs)

            # Проверяем время выполнения на аномалии
            execution_time = time.time() - start_time
            if execution_time < 0.09:  # Если быстрее чем задержка - подозрительно
                logger.warning(
                    f"Подозрительное время выполнения для {func.__name__}")

            return result

        self.protected_functions.append(func.__name__)
        return wrapper

    def protect_sensitive_operation(self, operation_name: str):
        """Декоратор для чувствительных операций"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                logger.info(f"Выполнение защищенной операции: {operation_name}")
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.error(
                        f"Ошибка в защищенной операции {operation_name}: {e}")
                    raise

            return wrapper
        return decorator
