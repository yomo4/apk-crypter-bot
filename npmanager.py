import logging
import re
import random
import string
import secrets
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class MythicalName(Enum):
    """Мифические имена для обфускации"""
    GORILA = "gorila"
    CHIMERA = "chimera"
    FENRIR = "fenrir"
    WYVERN = "wyvern"
    HYDRA = "hydra"
    KRAKEN = "kraken"
    PHOENIX = "phoenix"
    DRAGON = "dragon"
    GRIFFIN = "griffin"
    BASILISK = "basilisk"
    CERBERUS = "cerberus"
    SPHINX = "sphinx"
    LEVIATHAN = "leviathan"
    MEDUSA = "medusa"
    MINOTAUR = "minotaur"
    CYCLOPS = "cyclops"
    MANTICORE = "manticore"
    HARPY = "harpy"


class SystemServiceMask(Enum):
    """Маски под системные сервисы Android"""
    TECH_FRAMEWORK = "tech.framework.helper"
    ANDROID_SYSTEM = "android.system.service"
    ANDROID_INTERNAL = "com.android.internal.util"
    SYSTEM_CORE = "system.core.manager"
    FRAMEWORK_BASE = "framework.base.service"
    ANDROID_SERVICE = "com.android.service"
    SYSTEM_MANAGER = "system.manager.helper"


class NPMPackage:
    """NPM пакет для упаковки и защиты"""

    def __init__(self, package_name: Optional[str] = None):
        self.package_name = package_name or self._generate_masked_package_name()
        self.version = "3.0.61"
        self.protect_time = datetime.now()
        self.author = "吹牛儿"
        self.email = "2863678687@qq.com"
        self.qq_group = "832860549"
        self.function = "控制流混淆"
        self.logger = logging.getLogger(__name__)
        self.mythical_names = self._generate_mythical_names()
        self.fake_variables = self._generate_fake_variables()

    def _generate_masked_package_name(self) -> str:
        """Генерирует замаскированное имя пакета"""
        mask = random.choice(list(SystemServiceMask))
        return mask.value

    def _generate_mythical_names(self, count: int = 10) -> Dict[str, str]:
        """Генерирует соответствие реальных имен на мифические"""
        names = {}
        mythical_list = [m.value for m in MythicalName]
        
        for i in range(count):
            real_name = f"method_{i}"
            mythical = random.choice(mythical_list)
            names[real_name] = mythical
        
        return names

    def _generate_fake_variables(self, count: int = 5) -> Dict[str, int]:
        """Генерирует фейковые переменные"""
        fake_vars = {}
        for _ in range(count):
            var_name = random.choice(list(MythicalName)).value
            fake_vars[var_name] = random.randint(1000, 9999)
        
        return fake_vars

    def get_package_info(self) -> Dict:
        """Получает информацию о пакете"""
        return {
            "package_name": self.package_name,
            "version": self.version,
            "protect_time": self.protect_time,
            "author": self.author,
            "function": self.function,
            "mythical_names_count": len(self.mythical_names),
            "fake_variables_count": len(self.fake_variables)
        }


class NPManager:
    """
    NPManager - Упаковщик с защитой в стиле китайских упаковщиков
    Добавляет многоуровневую обфускацию и защиту
    """

    def __init__(self, package_name: Optional[str] = None):
        self.package = NPMPackage(package_name)
        self.logger = logging.getLogger(__name__)
        self.obfuscation_map = {}
        self.protected_code_cache = {}

    def obfuscate_function_names(self, code: str) -> Tuple[str, Dict[str, str]]:
        """Запутывает имена функций мифическими именами"""
        mapping = {}
        mythical_list = [m.value for m in MythicalName]
        
        # Находим все определения функций
        function_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        
        for match in re.finditer(function_pattern, code):
            original_name = match.group(1)
            if original_name not in mapping and not original_name.startswith('_'):
                mythical_name = random.choice(mythical_list)
                mapping[original_name] = mythical_name
        
        # Заменяем имена в коде
        for original, mythical in mapping.items():
            code = re.sub(r'\b' + original + r'\b', mythical, code)
        
        self.logger.info(f"Обфускировано {len(mapping)} функций")
        return code, mapping

    def add_fake_variables(self, code: str) -> str:
        """Добавляет фейковые переменные для запутывания"""
        fake_vars_code = "# Fake variables for obfuscation\n"
        
        for var_name, value in self.package.fake_variables.items():
            fake_vars_code += f"{var_name} = {value}\n"
            fake_vars_code += f"_{var_name} = {value} ^ {random.randint(1000, 9999)}\n"
        
        # Добавляем фейковые операции
        fake_vars_code += "\n# Fake operations\n"
        for _ in range(3):
            var = random.choice(list(self.package.fake_variables.keys()))
            fake_vars_code += f"_op_{secrets.token_hex(4)} = {var} * {random.randint(1, 100)} % {random.randint(1000, 9999)}\n"
        
        return fake_vars_code + code

    def add_control_flow_obfuscation(self, code: str) -> str:
        """Добавляет запутывание потока управления"""
        control_flow = """
def _control_flow_check():
    \"\"\"Control flow obfuscation\"\"\"
    """
        
        # Добавляем бесполезные вычисления
        for _ in range(5):
            var1 = random.randint(100, 9999)
            var2 = random.randint(100, 9999)
            operation = random.choice(['*', '+', '^', '%', '|', '&'])
            control_flow += f"    _x{_} = {var1} {operation} {var2}\n"
        
        control_flow += """
    return True

# Control flow wrapper
if _control_flow_check():
    pass
"""
        
        return control_flow + code

    def add_anti_analysis_checks(self, code: str) -> str:
        """Добавляет проверки против автоматического анализа"""
        checks = """
import time
import sys

def kraken_timing_check():
    \"\"\"Timing attack detection\"\"\"
    start = time.time()
    for i in range(1000):
        pass
    end = time.time()
    return (end - start) < 1.0

def basilisk_memory_check():
    \"\"\"Memory analysis detection\"\"\"
    import sys
    if sys.getsizeof(None) > 28:
        return False
    return True

def griffin_stack_check():
    \"\"\"Stack trace analysis detection\"\"\"
    stack = sys._getframe()
    depth = 0
    while stack:
        depth += 1
        if depth > 100:
            return False
        try:
            stack = stack.f_back
        except:
            break
    return True

# Execute checks
_check_kraken = kraken_timing_check()
_check_basilisk = basilisk_memory_check()
_check_griffin = griffin_stack_check()
"""
        
        return checks + code

    def add_fake_system_methods(self, code: str) -> str:
        """Добавляет фейковые системные методы"""
        fake_methods = f"""
def phoenix_system_service():
    \"\"\"Fake system service call\"\"\"
    time.sleep(0.025)

def leviathan_binder_call():
    \"\"\"Fake binder communication\"\"\"
    pass

def medusa_reflection_call():
    \"\"\"Fake reflection operation\"\"\"
    pass

def minotaur_thread_operation():
    \"\"\"Fake thread operation\"\"\"
    import threading
    t = threading.Thread(target=lambda: None)
    t.daemon = True
    t.start()

# Call fake methods for obfuscation
phoenix_system_service()
leviathan_binder_call()
medusa_reflection_call()
minotaur_thread_operation()
"""
        
        return code + fake_methods

    def dynamically_encode_strings(self, code: str) -> str:
        """Динамически кодирует строки"""
        # Находим все строковые литералы
        string_pattern = r'(["\'])([^"\']*)\1'
        
        encoded_strings = {}
        decoder_func = """
def _decode_string(encoded):
    \"\"\"Decode string obfuscation\"\"\"
    result = ""
    for char_code in encoded:
        result += chr(char_code)
    return result
"""
        
        result_code = decoder_func
        
        for match in re.finditer(string_pattern, code):
            original_string = match.group(2)
            if len(original_string) > 3:
                encoded = [ord(c) for c in original_string]
                encoded_strings[original_string] = encoded
        
        # Заменяем строки на вызовы декодера
        for original, encoded in encoded_strings.items():
            replacement = f'_decode_string({encoded})'
            code = code.replace(f'"{original}"', replacement)
            code = code.replace(f"'{original}'", replacement)
        
        return result_code + code

    def add_system_package_mask(self, code: str) -> str:
        """Добавляет маску под системный пакет"""
        mask_header = f"""
# Package: {self.package.package_name}
# Version: {self.package.version}
# Protected by NPManager v{self.package.version}
# Author: {self.package.author}
# Function: {self.package.function}

__package_name__ = "{self.package.package_name}"
__version__ = "{self.package.version}"
__protected__ = True
"""
        
        return mask_header + code

    def add_junk_methods(self, code: str, count: int = 5) -> str:
        """Добавляет ненужные методы для запутывания"""
        junk_code = "\n# Junk methods for obfuscation\n"
        
        for i in range(count):
            mythical = random.choice(list(MythicalName)).value
            junk_code += f"""
def {mythical}_junk_{i}():
    \"\"\"Junk method {i}\"\"\"
    """
            
            # Добавляем случайные операции
            for _ in range(random.randint(3, 7)):
                var = f"_x{secrets.token_hex(3)}"
                junk_code += f"    {var} = {random.randint(1, 1000)} * {random.randint(1, 1000)}\n"
            
            junk_code += "    return True\n"
        
        return code + junk_code

    def pack(self, code: str, aggressive: bool = True) -> str:
        """
        Упаковывает и защищает код
        
        Args:
            code: Исходный Python код
            aggressive: Агрессивная обфускация (больше защиты, медленнее)
        
        Returns:
            Защищенный и упакованный код
        """
        self.logger.info("Начинаю упаковку кода с NPManager")
        
        # Шаг 1: Добавляем маску системного пакета
        code = self.add_system_package_mask(code)
        
        # Шаг 2: Обфускируем имена функций
        code, name_mapping = self.obfuscate_function_names(code)
        self.obfuscation_map['names'] = name_mapping
        
        # Шаг 3: Добавляем фейковые переменные
        code = self.add_fake_variables(code)
        
        # Шаг 4: Добавляем контроль потока
        code = self.add_control_flow_obfuscation(code)
        
        if aggressive:
            # Шаг 5: Добавляем проверки анализа
            code = self.add_anti_analysis_checks(code)
            
            # Шаг 6: Добавляем фейковые системные методы
            code = self.add_fake_system_methods(code)
            
            # Шаг 7: Динамически кодируем строки
            code = self.dynamically_encode_strings(code)
            
            # Шаг 8: Добавляем мусорные методы
            code = self.add_junk_methods(code, count=5)
        
        self.logger.info("Упаковка завершена")
        self.protected_code_cache['packed'] = code
        
        return code

    def pack_file(self, file_path: Path, output_path: Optional[Path] = None, 
                  aggressive: bool = True) -> Path:
        """Упаковывает Python файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            
            packed_code = self.pack(code, aggressive=aggressive)
            
            if output_path is None:
                output_path = file_path.parent / f"{file_path.stem}_packed.py"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(packed_code)
            
            self.logger.info(f"Файл упакован: {output_path}")
            return output_path
        
        except Exception as e:
            self.logger.error(f"Ошибка при упаковке файла: {e}")
            raise

    def pack_directory(self, dir_path: Path, output_dir: Optional[Path] = None,
                      aggressive: bool = True) -> Dict[str, Path]:
        """Упаковывает все Python файлы в директории"""
        results = {}
        
        if output_dir is None:
            output_dir = dir_path.parent / f"{dir_path.name}_packed"
            output_dir.mkdir(exist_ok=True)
        
        for py_file in dir_path.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                try:
                    packed_path = self.pack_file(py_file, output_dir / py_file.name, aggressive)
                    results[str(py_file)] = packed_path
                except Exception as e:
                    self.logger.error(f"Ошибка при упаковке {py_file}: {e}")
        
        return results

    def generate_protection_marker(self) -> str:
        """Генерирует маркер защиты"""
        marker = f"""
# ProtectedByNPManager
# Author: {self.package.author}
# Email: {self.package.email}
# QQGroup: {self.package.qq_group}
# Function: {self.package.function}
# Version: {self.package.version}
# ProtectTime: {self.package.protect_time.strftime('%Y-%m-%d %H:%M')}
# Package: {self.package.package_name}
"""
        return marker

    def get_pack_report(self) -> Dict:
        """Получает отчет об упаковке"""
        return {
            "package_name": self.package.package_name,
            "version": self.package.version,
            "author": self.package.author,
            "protect_time": self.package.protect_time,
            "obfuscation_map": self.obfuscation_map,
            "mythical_names": self.package.mythical_names,
            "fake_variables": self.package.fake_variables,
            "protection_marker": self.generate_protection_marker()
        }


class NPManagerFactory:
    """Фабрика для создания NPManager инстансов"""

    @staticmethod
    def create_manager(package_name: Optional[str] = None) -> NPManager:
        """Создает новый NPManager инстанс"""
        return NPManager(package_name)

    @staticmethod
    def create_aggressive_manager(package_name: Optional[str] = None) -> NPManager:
        """Создает NPManager с максимальной защитой"""
        manager = NPManager(package_name)
        manager.logger.info("Режим максимальной защиты")
        return manager

    @staticmethod
    def create_light_manager(package_name: Optional[str] = None) -> NPManager:
        """Создает NPManager с легкой защитой"""
        manager = NPManager(package_name)
        manager.logger.info("Режим легкой защиты")
        return manager


class NPManagerBatchProcessor:
    """Пакетный обработчик для нескольких файлов"""

    def __init__(self, aggressive: bool = True):
        self.aggressive = aggressive
        self.results = {}
        self.logger = logging.getLogger(__name__)

    def process_batch(self, file_paths: List[Path], output_dir: Path) -> Dict:
        """Обрабатывает пакет файлов"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        for file_path in file_paths:
            try:
                manager = NPManager()
                packed_path = manager.pack_file(file_path, output_dir / file_path.name, 
                                               self.aggressive)
                self.results[str(file_path)] = {
                    "status": "success",
                    "output": str(packed_path)
                }
            except Exception as e:
                self.results[str(file_path)] = {
                    "status": "error",
                    "error": str(e)
                }
                self.logger.error(f"Ошибка при обработке {file_path}: {e}")
        
        return self.results

    def get_summary(self) -> Dict:
        """Получает сводку обработки"""
        successful = sum(1 for r in self.results.values() if r["status"] == "success")
        failed = sum(1 for r in self.results.values() if r["status"] == "error")
        
        return {
            "total": len(self.results),
            "successful": successful,
            "failed": failed,
            "results": self.results
        }


class TechFrameworkMasker:
    """
    Специализированный маскировщик для скрытия под tech.framework.helper
    Системный сервис Android для максимальной скрытности
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.package_name = "tech.framework.helper"
        self.manager = NPManager(package_name=self.package_name)

    def mask_code(self, code: str, aggressive: bool = True) -> str:
        """
        Маскирует код под системный сервис
        
        Args:
            code: Исходный Python код
            aggressive: Уровень агрессивности защиты
        
        Returns:
            Упакованный и замаскированный код
        """
        self.logger.info(
            f"Маскировка кода под {self.package_name}")
        return self.manager.pack(code, aggressive=aggressive)

    def mask_file(self, file_path: Path, output_path: Optional[Path] = None,
                  aggressive: bool = True) -> Path:
        """Маскирует Python файл"""
        self.logger.info(f"Маскировка файла: {file_path}")
        return self.manager.pack_file(file_path, output_path, aggressive)

    def mask_directory(self, dir_path: Path, output_dir: Optional[Path] = None,
                      aggressive: bool = True) -> Dict[str, Path]:
        """Маскирует директорию"""
        self.logger.info(f"Маскировка директории: {dir_path}")
        return self.manager.pack_directory(dir_path, output_dir, aggressive)

    def get_package_info(self) -> Dict:
        """Получает информацию о пакете для маскировки"""
        return {
            "package_name": self.package_name,
            "version": self.manager.package.version,
            "author": self.manager.package.author,
            "function": "Framework Helper Service",
            "description": "Android system framework helper service"
        }

    def get_protection_header(self) -> str:
        """Генерирует заголовок защиты для маскировки"""
        header = f"""
# {self.package_name}
# Version: {self.manager.package.version}
# Framework Helper Service
# Protected by NPManager

__package__ = "{self.package_name}"
__version__ = "{self.manager.package.version}"
__service_name__ = "FrameworkHelper"
__protected__ = True
"""
        return header

    def add_system_service_init(self, code: str) -> str:
        """Добавляет инициализацию системного сервиса"""
        init_code = f"""
import sys
import os

class {random.choice(['Service', 'Helper', 'Manager'])}:
    \"\"\"System framework service initialization\"\"\"
    
    def __init__(self):
        self._service_name = "{self.package_name}"
        self._initialized = False
    
    def initialize(self):
        if not self._initialized:
            self._initialized = True
        return self._initialized

_service = {random.choice(['Service', 'Helper', 'Manager'])}()
_service.initialize()
"""
        return init_code + code

    def create_masked_package(self, code: str, 
                            include_service_init: bool = True,
                            aggressive: bool = True) -> str:
        """
        Создает полностью замаскированный пакет
        
        Args:
            code: Исходный код
            include_service_init: Добавить инициализацию сервиса
            aggressive: Уровень защиты
        
        Returns:
            Полностью замаскированный код
        """
        # Добавляем заголовок защиты
        result = self.get_protection_header()
        
        # Добавляем инициализацию сервиса если нужно
        if include_service_init:
            result += self.add_system_service_init(code)
        else:
            result += code
        
        # Маскируем весь код
        masked = self.mask_code(result, aggressive=aggressive)
        
        self.logger.info("Пакет успешно замаскирован")
        return masked

    def get_masking_report(self) -> Dict:
        """Получает отчет о маскировке"""
        report = self.manager.get_pack_report()
        
        return {
            "masking_type": "tech.framework.helper",
            "package_name": self.package_name,
            "system_service": True,
            "description": "Android system framework helper service",
            **report
        }


class AndroidSystemMasker:
    """Маскировщик для различных Android системных сервисов"""

    @staticmethod
    def mask_as_tech_framework(code: str, aggressive: bool = True) -> str:
        """Маскирует под tech.framework.helper"""
        masker = TechFrameworkMasker()
        return masker.create_masked_package(code, aggressive=aggressive)

    @staticmethod
    def mask_as_android_system(code: str, aggressive: bool = True) -> str:
        """Маскирует под android.system.service"""
        manager = NPManager(package_name="android.system.service")
        return manager.pack(code, aggressive=aggressive)

    @staticmethod
    def mask_as_internal_util(code: str, aggressive: bool = True) -> str:
        """Маскирует под com.android.internal.util"""
        manager = NPManager(package_name="com.android.internal.util")
        return manager.pack(code, aggressive=aggressive)

    @staticmethod
    def mask_as_framework_base(code: str, aggressive: bool = True) -> str:
        """Маскирует под framework.base.service"""
        manager = NPManager(package_name="framework.base.service")
        return manager.pack(code, aggressive=aggressive)
