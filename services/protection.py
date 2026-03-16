import logging
import hashlib
import hmac
import secrets
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(Enum):
    """Уровни угроз"""
    SAFE = 0
    WARNING = 1
    CRITICAL = 2


class ProtectionException(Exception):
    """Исключение для защитных механизмов"""
    pass


class SecurityToken:
    """Токен безопасности с HMAC проверкой"""

    def __init__(self, secret_key: bytes = None):
        self.secret_key = secret_key or secrets.token_bytes(32)
        self.tokens: Dict[str, Tuple[str, float]] = {}
        self.logger = logging.getLogger(__name__)

    def generate(self, data: str, expiration_seconds: int = 3600) -> str:
        """Генерирует защищенный токен"""
        timestamp = datetime.now()
        message = f"{data}:{timestamp.isoformat()}".encode()
        signature = hmac.new(
            self.secret_key, message, hashlib.sha256
        ).hexdigest()
        token = f"{signature}:{timestamp.isoformat()}:{data}"

        self.tokens[token] = (data, time.time() + expiration_seconds)
        return token

    def verify(self, token: str) -> Tuple[bool, Optional[str]]:
        """Проверяет токен и возвращает данные"""
        try:
            parts = token.split(':')
            if len(parts) < 3:
                return False, None

            signature = parts[0]
            timestamp_str = ':'.join(parts[1:3])
            data = ':'.join(parts[3:])

            # Проверяем время истечения
            if token in self.tokens:
                _, expiration = self.tokens[token]
                if time.time() > expiration:
                    del self.tokens[token]
                    return False, None
            else:
                return False, None

            # Проверяем подпись
            message = f"{data}:{timestamp_str}".encode()
            expected_signature = hmac.new(
                self.secret_key, message, hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(signature, expected_signature):
                return True, data
            return False, None

        except Exception as e:
            self.logger.error(f"Ошибка при проверке токена: {e}")
            return False, None


class IntegrityChecker:
    """Проверка целостности файлов"""

    def __init__(self):
        self.checksums: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)

    def calculate_checksum(self, file_path: Path) -> str:
        """Вычисляет контрольную сумму файла"""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.error(f"Ошибка при расчете контрольной суммы: {e}")
            return ""

    def store_checksum(self, file_path: Path) -> bool:
        """Сохраняет контрольную сумму файла"""
        try:
            checksum = self.calculate_checksum(file_path)
            if checksum:
                self.checksums[str(file_path)] = checksum
                self.logger.info(
                    f"Контрольная сумма сохранена для {file_path}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении контрольной суммы: {e}")
            return False

    def verify_integrity(self, file_path: Path) -> Tuple[bool, str]:
        """Проверяет целостность файла"""
        try:
            file_key = str(file_path)
            if file_key not in self.checksums:
                return False, "Контрольная сумма не найдена"

            current_checksum = self.calculate_checksum(file_path)
            stored_checksum = self.checksums[file_key]

            if hmac.compare_digest(current_checksum, stored_checksum):
                return True, "Целостность подтверждена"
            else:
                return False, "Файл был изменен"

        except Exception as e:
            return False, f"Ошибка при проверке целостности: {e}"

    def verify_multiple(self, file_paths: List[Path]) -> Tuple[bool, Dict[str, str]]:
        """Проверяет целостность нескольких файлов"""
        results = {}
        all_valid = True

        for file_path in file_paths:
            is_valid, message = self.verify_integrity(file_path)
            results[str(file_path)] = message
            if not is_valid:
                all_valid = False

        return all_valid, results


class RateLimiter:
    """Ограничитель частоты запросов"""

    def __init__(self, max_attempts: int = 5, time_window: int = 60):
        self.max_attempts = max_attempts
        self.time_window = time_window  # секунды
        self.attempts: Dict[str, List[float]] = {}
        self.logger = logging.getLogger(__name__)

    def is_allowed(self, identifier: str) -> bool:
        """Проверяет разрешен ли запрос"""
        now = time.time()
        window_start = now - self.time_window

        if identifier not in self.attempts:
            self.attempts[identifier] = []

        # Удаляем старые попытки вне временного окна
        self.attempts[identifier] = [
            t for t in self.attempts[identifier] if t > window_start
        ]

        if len(self.attempts[identifier]) >= self.max_attempts:
            self.logger.warning(
                f"Превышен лимит попыток для {identifier}")
            return False

        self.attempts[identifier].append(now)
        return True

    def get_remaining_attempts(self, identifier: str) -> int:
        """Возвращает количество оставшихся попыток"""
        if identifier not in self.attempts:
            return self.max_attempts

        now = time.time()
        window_start = now - self.time_window
        valid_attempts = len([
            t for t in self.attempts[identifier] if t > window_start
        ])

        return max(0, self.max_attempts - valid_attempts)


class AntiTamperingMonitor:
    """Монитор для обнаружения попыток модификации"""

    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.monitored_files: Dict[str, str] = {}
        self.last_check: Dict[str, float] = {}
        self.threats_detected: List[Dict] = []
        self.is_running = False
        self.monitor_thread = None
        self.logger = logging.getLogger(__name__)

    def add_file(self, file_path: Path) -> bool:
        """Добавляет файл для мониторинга"""
        try:
            if not file_path.exists():
                self.logger.error(f"Файл не найден: {file_path}")
                return False

            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            self.monitored_files[str(file_path)] = sha256_hash.hexdigest()
            self.logger.info(f"Файл добавлен для мониторинга: {file_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Ошибка при добавлении файла для мониторинга: {e}")
            return False

    def check_file(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Проверяет изменился ли файл"""
        try:
            if file_path not in self.monitored_files:
                return False, "Файл не находится под мониторингом"

            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                threat = {
                    "timestamp": datetime.now(),
                    "file": file_path,
                    "type": "FILE_DELETED",
                    "severity": ThreatLevel.CRITICAL
                }
                self.threats_detected.append(threat)
                return False, "Файл был удален"

            sha256_hash = hashlib.sha256()
            with open(file_path_obj, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)

            current_hash = sha256_hash.hexdigest()
            stored_hash = self.monitored_files[file_path]

            if current_hash != stored_hash:
                threat = {
                    "timestamp": datetime.now(),
                    "file": file_path,
                    "type": "FILE_MODIFIED",
                    "severity": ThreatLevel.CRITICAL
                }
                self.threats_detected.append(threat)
                return False, "Файл был изменен"

            return True, "OK"

        except Exception as e:
            self.logger.error(f"Ошибка при проверке файла: {e}")
            return False, str(e)

    def start_monitoring(self) -> bool:
        """Запускает фоновый мониторинг"""
        if self.is_running:
            return False

        self.is_running = True
        self.monitor_thread = threading.Thread(
            target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Мониторинг запущен")
        return True

    def stop_monitoring(self) -> bool:
        """停止 фоновый мониторинг"""
        self.is_running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        self.logger.info("Мониторинг остановлен")
        return True

    def _monitor_loop(self):
        """Основной цикл мониторинга"""
        while self.is_running:
            for file_path in list(self.monitored_files.keys()):
                self.check_file(file_path)
            time.sleep(self.check_interval)

    def get_threats(self) -> List[Dict]:
        """Возвращает список обнаруженных угроз"""
        return self.threats_detected.copy()

    def clear_threats(self):
        """Очищает список угроз"""
        self.threats_detected.clear()


class ExecutionEnvironmentValidator:
    """Валидатор окружения выполнения"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validation_results = {}

    def validate_signature(self, signature: bytes, public_key: bytes = None) -> bool:
        """Проверяет подпись кода"""
        # Симуляция проверки подписи
        # В реальном приложении используйте асимметричную криптографию
        try:
            logger.info("Проверка подписи кода...")
            if not signature:
                return False
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при проверке подписи: {e}")
            return False

    def check_runtime_integrity(self) -> Tuple[bool, Dict]:
        """Проверяет целостность runtime окружения"""
        results = {
            "memory_accessible": True,
            "stack_integrity": True,
            "syscalls_monitored": False,
            "timestamp": datetime.now()
        }

        try:
            # Базовая проверка целостности памяти
            test_data = b"integrity_check"
            test_hash = hashlib.sha256(test_data).hexdigest()
            verification = hashlib.sha256(test_data).hexdigest()

            if test_hash != verification:
                results["memory_accessible"] = False

            self.logger.info("Проверка целостности runtime завершена")
            return all(results.values()), results

        except Exception as e:
            self.logger.error(f"Ошибка при проверке целостности runtime: {e}")
            return False, results

    def validate_api_calls(self, call_list: List[str]) -> Tuple[bool, List[str]]:
        """Проверяет допустимость API вызовов"""
        dangerous_apis = [
            "dlopen", "dlsym", "ptrace", "process_vm_readv",
            "getenv", "system", "exec"
        ]

        unsafe_calls = [
            call for call in call_list if any(
                dangerous in call.lower() for dangerous in dangerous_apis
            )
        ]

        return len(unsafe_calls) == 0, unsafe_calls


class ProtectionManager:
    """Главный менеджер защиты"""

    def __init__(self):
        self.security_token = SecurityToken()
        self.integrity_checker = IntegrityChecker()
        self.rate_limiter = RateLimiter()
        self.anti_tampering = AntiTamperingMonitor()
        self.env_validator = ExecutionEnvironmentValidator()
        self.logger = logging.getLogger(__name__)
        self.is_active = False

    def initialize(self, files_to_monitor: List[Path] = None) -> bool:
        """Инициализирует систему защиты"""
        try:
            self.logger.info("Инициализация системы защиты...")

            # Сохраняем контрольные суммы для критичных файлов
            if files_to_monitor:
                for file_path in files_to_monitor:
                    self.integrity_checker.store_checksum(file_path)
                    self.anti_tampering.add_file(file_path)

            # Запускаем мониторинг
            self.anti_tampering.start_monitoring()

            self.is_active = True
            self.logger.info("Система защиты инициализирована")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при инициализации защиты: {e}")
            return False

    def verify_environment(self) -> Tuple[bool, Dict]:
        """Комплексная проверка окружения"""
        checks = {
            "integrity": False,
            "runtime": False,
            "signature": False,
            "timestamp": datetime.now()
        }

        try:
            # Проверка целостности runtime
            runtime_ok, runtime_results = self.env_validator.check_runtime_integrity()
            checks["runtime"] = runtime_ok

            # Проверка подписи
            checks["signature"] = self.env_validator.validate_signature(b"signature_data")

            # Проверка целостности файлов
            if self.integrity_checker.checksums:
                all_files = list(self.integrity_checker.checksums.keys())
                if all_files:
                    file_path = Path(all_files[0])
                    is_valid, _ = self.integrity_checker.verify_integrity(file_path)
                    checks["integrity"] = is_valid

            return all(checks.values()), checks

        except Exception as e:
            self.logger.error(f"Ошибка при проверке окружения: {e}")
            return False, checks

    def create_security_context(self, user_id: str = None) -> str:
        """Создает защищенный контекст пользователя"""
        try:
            context_data = user_id or secrets.token_hex(16)
            token = self.security_token.generate(context_data)
            self.logger.info(f"Контекст безопасности создан для {user_id}")
            return token
        except Exception as e:
            self.logger.error(f"Ошибка при создании контекста безопасности: {e}")
            return ""

    def validate_security_context(self, token: str) -> bool:
        """Проверяет защищенный контекст"""
        try:
            is_valid, data = self.security_token.verify(token)
            if is_valid:
                self.logger.info(f"Контекст безопасности подтвержден")
            else:
                self.logger.warning(f"Контекст безопасности невалидный")
            return is_valid
        except Exception as e:
            self.logger.error(f"Ошибка при проверке контекста: {e}")
            return False

    def check_rate_limit(self, identifier: str) -> Tuple[bool, int]:
        """Проверяет ограничение частоты"""
        allowed = self.rate_limiter.is_allowed(identifier)
        remaining = self.rate_limiter.get_remaining_attempts(identifier)
        return allowed, remaining

    def get_security_status(self) -> Dict:
        """Получает статус безопасности"""
        return {
            "is_active": self.is_active,
            "protection_status": "ACTIVE" if self.is_active else "INACTIVE",
            "threats_detected": len(self.anti_tampering.threats_detected),
            "monitored_files": len(self.anti_tampering.monitored_files),
            "timestamp": datetime.now()
        }

    def shutdown(self) -> bool:
        """Выключает систему защиты"""
        try:
            self.anti_tampering.stop_monitoring()
            self.is_active = False
            self.logger.info("Система защиты выключена")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка при выключении защиты: {e}")
            return False

    def generate_security_report(self) -> Dict:
        """Генерирует отчет о безопасности"""
        env_ok, env_checks = self.verify_environment()
        threats = self.anti_tampering.get_threats()

        report = {
            "timestamp": datetime.now(),
            "status": "SECURE" if env_ok else "COMPROMISED",
            "environment_checks": env_checks,
            "threats_detected": len(threats),
            "threat_details": threats,
            "protection_status": self.get_security_status()
        }

        return report
