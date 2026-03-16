"""
Примеры использования защитного слоя CRUPTOANON
"""

from pathlib import Path
from services import (
    ProtectionManager,
    AndroidEnvironmentDetector,
    AntiAnalysisProtection,
    ObfuscationManager,
    NPManager,
    SystemServiceMask,
)


def example_basic_protection():
    """Пример базовой защиты"""
    print("=== Пример 1: Базовая защита ===\n")

    # Инициализируем менеджер защиты
    protection_manager = ProtectionManager()

    # Список файлов для мониторинга
    files_to_monitor = [
        Path("main.py"),
        Path("config.py"),
    ]

    # Инициализируем защиту
    protection_manager.initialize(files_to_monitor)
    print("✓ Защита инициализирована\n")

    # Создаем токен безопасности
    token = protection_manager.create_security_context("user_123")
    print(f"✓ Токен безопасности создан: {token[:50]}...\n")

    # Проверяем окружение
    env_ok, checks = protection_manager.verify_environment()
    print(f"✓ Проверка окружения: {'SAFE' if env_ok else 'UNSAFE'}")
    print(f"  Результаты: {checks}\n")

    # Получаем статус безопасности
    status = protection_manager.get_security_status()
    print(f"✓ Статус защиты:")
    for key, value in status.items():
        print(f"  {key}: {value}")

    print()


def example_android_detection():
    """Пример обнаружения Android угроз"""
    print("=== Пример 2: Обнаружение Android угроз ===\n")

    detector = AndroidEnvironmentDetector()

    # Проверка отладчика
    print("Проверка отладчика...")
    debugger_detected, message = detector.detect_debugger()
    print(f"Отладчик: {'ОБНАРУЖЕН' if debugger_detected else 'НЕ обнаружен'}")
    if message:
        print(f"  Деталь: {message}\n")
    else:
        print()

    # Проверка эмулятора
    print("Проверка эмулятора...")
    emulator_detected, indicators = detector.detect_emulator()
    print(f"Эмулятор: {'ОБНАРУЖЕН' if emulator_detected else 'НЕ обнаружен'}")
    if indicators:
        for indicator in indicators:
            print(f"  - {indicator}\n")
    else:
        print()

    # Проверка root
    print("Проверка Root...")
    root_detected, indicators = detector.detect_root()
    print(f"Root: {'ОБНАРУЖЕН' if root_detected else 'НЕ обнаружен'}")
    if indicators:
        for indicator in indicators:
            print(f"  - {indicator}\n")
    else:
        print()

    # Полная проверка
    print("Выполнение полной проверки...")
    is_safe, detections = detector.perform_full_scan()
    print(f"Статус окружения: {'БЕЗОПАСНО' if is_safe else 'КОМПРОМЕТИРОВАНО'}")
    print(f"Обнаружено угроз: {len(detections)}\n")

    # Получение отчета
    report = detector.get_detection_report()
    print("Отчет об обнаружении:")
    print(f"  Статус: {report['status']}")
    print(f"  Всего обнаружено: {report['detections_count']}")
    for detection in report['detections']:
        print(f"  - {detection['type']}: {detection['indicators']}\n")


def example_code_obfuscation():
    """Пример обфускации кода"""
    print("=== Пример 3: Обфускация кода ===\n")

    manager = ObfuscationManager()

    # Примерный код
    sample_code = """
def calculate_sum(a, b):
    \"\"\"Вычисляет сумму двух чисел\"\"\"
    # Складываем числа
    result = a + b
    return result

def main():
    value1 = 10
    value2 = 20
    total = calculate_sum(value1, value2)
    print(f"Результат: {total}")
"""

    print("Исходный код:")
    print(sample_code)
    print("\n" + "="*50 + "\n")

    # Обфускируем
    obfuscated = manager.code_obfuscator.obfuscate(sample_code, aggressive=False)

    print("Обфускированный код:")
    print(obfuscated)
    print()


def example_rate_limiting():
    """Пример ограничения частоты запросов"""
    print("=== Пример 4: Ограничение частоты запросов ===\n")

    protection_manager = ProtectionManager()

    # Проверяем rate limit
    user_id = "user_456"
    print(f"Пользователь: {user_id}")
    print(f"Максимум попыток: 5 за 60 секунд\n")

    for i in range(8):
        allowed, remaining = protection_manager.check_rate_limit(user_id)
        status = "✓ РАЗРЕШЕНО" if allowed else "✗ ЗАБЛОКИРОВАНО"
        print(f"Попытка {i+1}: {status} | Осталось: {remaining}")

    print()


def example_anti_analysis():
    """Пример защиты от анализа"""
    print("=== Пример 5: Защита от анализа ===\n")

    anti_analysis = AntiAnalysisProtection()

    sample_code = """
def sensitive_operation():
    secret_key = "TOP_SECRET_KEY"
    return secret_key
"""

    print("Исходный код:")
    print(sample_code)
    print("\n" + "="*50 + "\n")

    # Добавляем проверки анализа
    protected = anti_analysis.add_anti_analysis_checks(sample_code)

    print("Код с защитой от анализа:")
    print(protected)
    print()

    # Запутываем поток управления
    obfuscated_flow = anti_analysis.obfuscate_flow(sample_code)
    print("\nКод с запутанным потоком управления:")
    print(obfuscated_flow)
    print()


def example_security_report():
    """Пример генерации отчета безопасности"""
    print("=== Пример 6: Отчет безопасности ===\n")

    protection_manager = ProtectionManager()
    protection_manager.initialize()

    report = protection_manager.generate_security_report()

    print("ОТЧЕТ БЕЗОПАСНОСТИ")
    print("=" * 50)
    print(f"Время: {report['timestamp']}")
    print(f"Статус: {report['status']}")
    print(f"Обнаружено угроз: {report['threats_detected']}\n")

    print("ПРОВЕРКИ ОКРУЖЕНИЯ:")
    for key, value in report['environment_checks'].items():
        print(f"  {key}: {value}")

    print("\nДЕТАЛИ ЗАЩИТЫ:")
    for key, value in report['protection_status'].items():
        print(f"  {key}: {value}")

    print()


def example_system_package_masking():
    """Пример маскировки под системный сервис"""
    print("=== Пример 7: Маскировка пакета под системный сервис ===\n")

    sample_code = """
def get_user_data(user_id):
    '''Получить данные пользователя'''
    return {"id": user_id, "name": "User"}

def process_payment(amount, card):
    '''Обработать платеж'''
    return {"status": "success", "amount": amount}

def authenticate():
    '''Аутентификация'''
    return True
"""

    print("Исходный код:")
    print(sample_code)
    print("\n" + "="*60 + "\n")

    # Маскируем под системный сервис tech.framework.helper
    manager = NPManager(package_name="tech.framework.helper")
    
    print(f"Маскировка пакета: {manager.package.package_name}")
    print(f"Версия защиты: {manager.package.version}")
    print(f"Автор: {manager.package.author}\n")

    # Упаковываем с маскировкой
    packed_code = manager.pack(sample_code, aggressive=True)
    
    print("Упакованный код с маскировкой (первые 500 символов):")
    print(packed_code[:500])
    print("...\n")

    # Получаем маркер защиты
    marker = manager.generate_protection_marker()
    print("Маркер защиты:")
    print(marker)
    print()

    # Показываем все доступные маски
    print("Доступные маски системных пакетов:")
    for mask in SystemServiceMask:
        print(f"  - {mask.value}")
    print()


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ЗАЩИТНОГО СЛОЯ CRUPTOANON")
    print("="*60 + "\n")

    try:
        example_basic_protection()
    except Exception as e:
        print(f"Ошибка в примере 1: {e}\n")

    try:
        example_android_detection()
    except Exception as e:
        print(f"Ошибка в примере 2: {e}\n")

    try:
        example_code_obfuscation()
    except Exception as e:
        print(f"Ошибка в примере 3: {e}\n")

    try:
        example_rate_limiting()
    except Exception as e:
        print(f"Ошибка в примере 4: {e}\n")

    try:
        example_anti_analysis()
    except Exception as e:
        print(f"Ошибка в примере 5: {e}\n")

    try:
        example_security_report()
    except Exception as e:
        print(f"Ошибка в примере 6: {e}\n")

    try:
        example_system_package_masking()
    except Exception as e:
        print(f"Ошибка в примере 7: {e}\n")

    print("="*60)
    print("Все примеры завершены!")
    print("="*60)
