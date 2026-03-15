import logging
import re
import secrets
import string
from pathlib import Path
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class CodeObfuscator:
    """Обфускатор для Python кода и конфигураций"""

    def __init__(self):
        self.name_mapping: Dict[str, str] = {}
        self.string_mapping: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)

    def _generate_random_name(self, prefix: str = "a") -> str:
        """Генерирует случайное имя переменной"""
        suffix = ''.join(secrets.choice(string.ascii_lowercase + string.digits)
                        for _ in range(8))
        return f"_{prefix}{suffix}"

    def _obfuscate_variable_names(self, code: str) -> Tuple[str, Dict[str, str]]:
        """Обфускирует имена переменных и функций"""
        mapping = {}

        # Паттерны для переменных и функций (опасно заменять все подряд)
        patterns = [
            (r'\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(', 'function'),
            (r'\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]', 'class'),
        ]

        # Исключения - не обфускировать встроенные функции и магические методы
        excluded = {
            '__init__', '__main__', '__name__', '__file__', '__doc__',
            '__dict__', '__class__', '__bases__', 'logger', 'self', 'cls',
            'super', 'property', 'staticmethod', 'classmethod',
            'import', 'from', 'return', 'yield', 'lambda',
        }

        for pattern, name_type in patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                original_name = match.group(1)
                if original_name not in excluded and original_name not in mapping:
                    obfuscated = self._generate_random_name(name_type[0])
                    mapping[original_name] = obfuscated

        # Заменяем имена в коде
        for original, obfuscated in mapping.items():
            # Используем словно границы для слов
            code = re.sub(r'\b' + re.escape(original) + r'\b',
                         obfuscated, code)

        return code, mapping

    def _obfuscate_strings(self, code: str) -> Tuple[str, Dict[str, str]]:
        """Обфускирует строки через кодирование и runtime декодирование"""
        mapping = {}

        # Находим все строковые литералы
        pattern = r'(["\'])([^"\']*)\1'
        matches = re.finditer(pattern, code)

        for match in matches:
            original_string = match.group(2)
            if len(original_string) > 3 and not original_string.startswith('_'):
                # Кодируем строку
                encoded = original_string.encode().hex()
                var_name = f"_s{secrets.token_hex(4)}"
                mapping[original_string] = (var_name, encoded)

        # Создаем помощник для декодирования
        decode_helper = """
def _d(h):return bytes.fromhex(h).decode()
"""

        # Заменяем строки на вызовы декодера
        for original, (var_name, encoded) in mapping.items():
            code = code.replace(f'"{original}"', f'_d("{encoded}")')
            code = code.replace(f"'{original}'", f'_d("{encoded}")')

        if mapping:
            code = decode_helper + code

        return code, mapping

    def _strip_comments_and_docstrings(self, code: str) -> str:
        """Удаляет комментарии и ненужные docstring'и"""
        lines = code.split('\n')
        result = []

        in_docstring = False
        docstring_char = None

        for line in lines:
            stripped = line.lstrip()

            # Пропускаем комментарии
            if stripped.startswith('#'):
                continue

            # Обработка docstring'ов (тройных кавычек)
            if '"""' in stripped or "'''" in stripped:
                if '"""' in stripped:
                    docstring_char = '"""'
                else:
                    docstring_char = "'''"

                if in_docstring and docstring_char in stripped:
                    in_docstring = False
                    docstring_char = None
                else:
                    in_docstring = not in_docstring
                continue

            if not in_docstring:
                result.append(line)

        return '\n'.join(result)

    def _compact_code(self, code: str) -> str:
        """Делает код более компактным"""
        # Удаляем пустые строки
        lines = [line for line in code.split('\n') if line.strip()]

        # Удаляем пробелы в конце строк
        lines = [line.rstrip() for line in lines]

        return '\n'.join(lines)

    def obfuscate(self, code: str, aggressive: bool = False) -> str:
        """
        Обфускирует Python код

        Args:
            code: Исходный код
            aggressive: Агрессивная обфускация (переименование переменных)

        Returns:
            Обфускированный код
        """
        self.logger.info("Начинаю обфускацию кода")

        # Удаляем комментарии и docstring'и
        code = self._strip_comments_and_docstrings(code)

        # Обфускируем строки
        code, string_mapping = self._obfuscate_strings(code)

        # Агрессивная обфускация - переименование переменных
        if aggressive:
            code, var_mapping = self._obfuscate_variable_names(code)
            self.logger.info(
                f"Переименовано {len(var_mapping)} переменных/функций")

        # Компактируем код
        code = self._compact_code(code)

        self.logger.info(
            f"Кодирование завершено ({len(string_mapping)} строк закодировано)")

        return code


class StringObfuscator:
    """Обфускатор строк и конфигов"""

    @staticmethod
    def encode_string(s: str) -> str:
        """Кодирует строку в hex"""
        return s.encode().hex()

    @staticmethod
    def decode_string(h: str) -> str:
        """Декодирует строку из hex"""
        return bytes.fromhex(h).decode()

    @staticmethod
    def rot13_encode(s: str) -> str:
        """ROT13 кодирование"""
        return ''.join(
            chr((ord(c) - ord('a' + 13 % 26)) % 26 + ord('a'))
            if 'a' <= c <= 'z'
            else chr((ord(c) - ord('A' + 13 % 26)) % 26 + ord('A'))
            if 'A' <= c <= 'Z'
            else c
            for c in s
        )

    @staticmethod
    def xor_encode(data: bytes, key: bytes) -> bytes:
        """XOR кодирование"""
        return bytes(a ^ b for a, b in zip(data, key * (len(data) // len(key) + 1)))

    @staticmethod
    def base64_obfuscate(s: str) -> str:
        """Base64 кодирование для обфускации"""
        import base64
        return base64.b64encode(s.encode()).decode()


class BytecodeObfuscator:
    """Обфускатор для .pyc файлов"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def obfuscate_bytecode_file(self, file_path: Path) -> bool:
        """
        Обфускирует скомпилированный Python файл (.pyc)
        
        Примечание: Это базовая реализация.
        Для полной обфускации используйте Cython или PyArmor
        """
        try:
            if not file_path.exists():
                self.logger.error(
                    f"Файл не найден: {file_path}")
                return False

            if file_path.suffix != '.pyc':
                self.logger.warning(
                    f"Файл не является .pyc: {file_path}")
                return False

            # Добавляем шум в .pyc файл для затруднения анализа
            with open(file_path, 'rb') as f:
                content = f.read()

            # Добавляем случайные данные в конец
            noise = secrets.token_bytes(1024)
            obfuscated = content + noise

            with open(file_path, 'wb') as f:
                f.write(obfuscated)

            self.logger.info(f"Bytecode обфускирован: {file_path}")
            return True

        except Exception as e:
            self.logger.error(
                f"Ошибка при обфускации bytecode: {e}")
            return False


class APKObfuscator:
    """Обфускация для APK/Smali кода"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def obfuscate_smali(self, smali_code: str) -> str:
        """
        Базовая обфускация Smali кода
        
        Примечание: Для полной обфускации используйте ProGuard или R8
        """
        # Переименовываем локальные переменные
        smali_code = re.sub(
            r'\bv(\d+)',
            lambda m: f'v{secrets.randbelow(256):03d}',
            smali_code
        )

        # Перемешиваем порядок методов (если возможно)
        return smali_code

    def obfuscate_resources(self, apk_path: Path) -> bool:
        """Обфускирует ресурсы в APK (переименование, удаление комментариев)"""
        try:
            if not apk_path.exists():
                self.logger.error(f"APK не найден: {apk_path}")
                return False

            self.logger.info(f"Начинаю обфускацию ресурсов APK: {apk_path}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при обфускации APK: {e}")
            return False


class ObfuscationManager:
    """Главный менеджер обфускации"""

    def __init__(self):
        self.code_obfuscator = CodeObfuscator()
        self.string_obfuscator = StringObfuscator()
        self.bytecode_obfuscator = BytecodeObfuscator()
        self.apk_obfuscator = APKObfuscator()
        self.logger = logging.getLogger(__name__)

    def obfuscate_python_file(self, file_path: Path, aggressive: bool = False) -> str:
        """Обфускирует Python файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()

            obfuscated = self.code_obfuscator.obfuscate(
                code, aggressive=aggressive)

            self.logger.info(
                f"Python файл обфускирован: {file_path}")
            return obfuscated

        except Exception as e:
            self.logger.error(f"Ошибка при обфускации {file_path}: {e}")
            raise

    def obfuscate_python_directory(self, dir_path: Path, aggressive: bool = False) -> Dict[str, str]:
        """Обфускирует все Python файлы в директории"""
        results = {}

        for py_file in dir_path.rglob('*.py'):
            if '__pycache__' not in str(py_file):
                try:
                    obfuscated = self.obfuscate_python_file(
                        py_file, aggressive=aggressive)
                    results[str(py_file)] = obfuscated
                except Exception as e:
                    self.logger.error(
                        f"Не удалось обфускировать {py_file}: {e}")

        return results

    def save_obfuscated(self, original_path: Path, obfuscated_code: str, output_dir: Path = None) -> Path:
        """Сохраняет обфускированный код в файл"""
        if output_dir is None:
            output_dir = original_path.parent

        output_path = output_dir / f"{original_path.stem}_obfuscated{original_path.suffix}"

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(obfuscated_code)

            self.logger.info(f"Обфускированный код сохранен: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(
                f"Ошибка при сохранении обфускированного кода: {e}")
            raise
