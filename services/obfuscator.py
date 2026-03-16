import logging
import re
import random
import string
import base64
from typing import Dict, List

logger = logging.getLogger(__name__)


class CodeObfuscator:
    """Обфускатор Python/Java кода"""

    def __init__(self):
        self.var_map: Dict[str, str] = {}
        self.func_map: Dict[str, str] = {}
        self._counter = 0

    def _new_name(self, prefix: str = "v") -> str:
        """Генерирует уникальное обфусцированное имя"""
        self._counter += 1
        suffix = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        return f"_{prefix}{self._counter}_{suffix}"

    def _encode_string(self, s: str) -> str:
        """Кодирует строку в hex escape"""
        encoded = base64.b64encode(s.encode()).decode()
        return f'__import__("base64").b64decode("{encoded}").decode()'

    def obfuscate_variables(self, code: str) -> str:
        """Переименовывает локальные переменные"""
        # Только простые переменные (не встроенные, не импорты)
        skip = {
            "self", "cls", "None", "True", "False", "and", "or", "not",
            "in", "is", "if", "else", "elif", "for", "while", "return",
            "import", "from", "as", "class", "def", "try", "except",
            "finally", "with", "pass", "break", "continue", "raise",
            "lambda", "yield", "global", "nonlocal", "del", "print",
        }
        pattern = re.compile(r'\b([a-z][a-z0-9_]{2,})\b')

        def replace(m):
            name = m.group(1)
            if name in skip:
                return name
            if name not in self.var_map:
                self.var_map[name] = self._new_name("x")
            return self.var_map[name]

        return pattern.sub(replace, code)

    def obfuscate_function_names(self, code: str) -> str:
        """Переименовывает пользовательские функции"""
        pattern = re.compile(r'\bdef\s+([a-z][a-z0-9_]+)\s*\(')

        def replace(m):
            name = m.group(1)
            if name not in self.func_map:
                self.func_map[name] = self._new_name("f")
            return f"def {self.func_map[name]}("

        return pattern.sub(replace, code)

    def encode_strings(self, code: str) -> str:
        """Кодирует строковые литералы"""
        # Обрабатываем только простые однострочные строки
        def replace_string(m):
            content = m.group(1) or m.group(2)
            if not content or len(content) > 200:
                return m.group(0)
            try:
                encoded = base64.b64encode(content.encode()).decode()
                return f'__import__("base64").b64decode("{encoded}").decode()'
            except Exception:
                return m.group(0)

        pattern = re.compile(r'"([^"\\]{1,200})"|\'([^\'\\]{1,200})\'')
        return pattern.sub(replace_string, code)

    def add_junk_imports(self) -> str:
        """Возвращает мусорные импорты"""
        junk_names = ["os", "sys", "hashlib", "time", "math"]
        lines = []
        for name in random.sample(junk_names, 3):
            alias = self._new_name("m")
            lines.append(f"import {name} as {alias}  # noqa")
        return "\n".join(lines) + "\n"

    def obfuscate(self, code: str, aggressive: bool = True) -> str:
        """
        Полная обфускация кода

        Args:
            code: Исходный код
            aggressive: True = полная обфускация, False = лёгкая

        Returns:
            Обфусцированный код
        """
        if not code:
            return code

        result = code

        if aggressive:
            # Агрессивная: переименование функций + переменных + мусорные импорты
            try:
                result = self.obfuscate_function_names(result)
            except Exception as e:
                logger.warning(f"obfuscate_function_names failed: {e}")

            try:
                result = self.obfuscate_variables(result)
            except Exception as e:
                logger.warning(f"obfuscate_variables failed: {e}")

            result = self.add_junk_imports() + result
        else:
            # Лёгкая: только переименование переменных
            try:
                result = self.obfuscate_variables(result)
            except Exception as e:
                logger.warning(f"obfuscate_variables failed: {e}")

        logger.info(f"Обфускация завершена (aggressive={aggressive})")
        return result


class ObfuscationManager:
    """Менеджер обфускации — агрегирует кодовый и другие обфускаторы"""

    def __init__(self):
        self.code_obfuscator = CodeObfuscator()
        self.logger = logging.getLogger(__name__)

    def obfuscate_file(self, file_path: str, aggressive: bool = True) -> str:
        """Обфусцирует файл и возвращает результат"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return self.code_obfuscator.obfuscate(code, aggressive=aggressive)
        except Exception as e:
            self.logger.error(f"Ошибка обфускации файла {file_path}: {e}")
            return ""

    def get_stats(self) -> dict:
        """Возвращает статистику обфускации"""
        return {
            "variables_renamed": len(self.code_obfuscator.var_map),
            "functions_renamed": len(self.code_obfuscator.func_map),
        }
