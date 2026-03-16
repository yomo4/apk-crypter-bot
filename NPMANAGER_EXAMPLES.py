"""
Примеры использования NPManager упаковщика
"""

from pathlib import Path
from services import NPManager, NPManagerFactory, NPManagerBatchProcessor


def example_basic_packing():
    """Пример базовой упаковки"""
    print("=== Пример 1: Базовая упаковка ===\n")

    sample_code = """
def authenticate_user(username, password):
    '''Authenticate user'''
    if username == "admin" and password == "secret123":
        return True
    return False

def process_data(data):
    '''Process sensitive data'''
    result = []
    for item in data:
        result.append(item * 2)
    return result

def main():
    users = ["user1", "user2", "user3"]
    for user in users:
        print(f"Processing {user}")
    
    data = [1, 2, 3, 4, 5]
    result = process_data(data)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""

    print("Исходный код:")
    print(sample_code)
    print("\n" + "="*60 + "\n")

    # Создаем и упаковываем
    manager = NPManager()
    packed_code = manager.pack(sample_code, aggressive=False)

    print("Упакованный код:")
    print(packed_code[:500] + "\n... (обрезано для brevity)\n")


def example_aggressive_packing():
    """Пример агрессивной упаковки"""
    print("=== Пример 2: Агрессивная упаковка ===\n")

    code = """
def get_api_key():
    return "sk-1234567890abcdef"

def make_request(endpoint, data):
    # Make API request
    pass
"""

    print("Исходный код:")
    print(code)
    print("\n" + "="*60 + "\n")

    # Агрессивная упаковка
    manager = NPManager(package_name="com.android.internal.util")
    packed = manager.pack(code, aggressive=True)

    print("Агрессивно упакованный код (первые 600 символов):")
    print(packed[:600] + "\n... (обрезано)\n")

    # Получаем отчет
    report = manager.get_pack_report()
    print("ОТЧЕТ ОБ УПАКОВКЕ:")
    print(f"Пакет: {report['package_name']}")
    print(f"Версия: {report['version']}")
    print(f"Автор: {report['author']}")
    print(f"Время защиты: {report['protect_time']}\n")

    print("Обфускированные имена функций:")
    for original, mythical in list(report['obfuscation_map'].get('names', {}).items())[:3]:
        print(f"  {original} -> {mythical}")
    print()


def example_factory_creation():
    """Пример создания через фабрику"""
    print("=== Пример 3: Создание через фабрику ===\n")

    code = "def secret_function(): return 42"

    # Обычный менеджер
    manager1 = NPManagerFactory.create_manager()
    print(f"Обычный менеджер: {manager1.package.package_name}")

    # Агрессивный менеджер
    manager2 = NPManagerFactory.create_aggressive_manager()
    print(f"Агрессивный менеджер: {manager2.package.package_name}")

    # Легкий менеджер
    manager3 = NPManagerFactory.create_light_manager()
    print(f"Легкий менеджер: {manager3.package.package_name}\n")


def example_file_packing():
    """Пример упаковки файла"""
    print("=== Пример 4: Упаковка файла ===\n")

    # Создаем тестовый файл
    test_file = Path("temp") / "test_code.py"
    test_file.parent.mkdir(exist_ok=True)

    test_code = """
def calculate(x, y):
    return x + y

def main():
    result = calculate(10, 20)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""

    with open(test_file, 'w') as f:
        f.write(test_code)

    print(f"Создан тестовый файл: {test_file}\n")

    # Упаковываем файл
    manager = NPManager()
    output_file = test_file.parent / "test_code_packed.py"
    
    try:
        packed_path = manager.pack_file(test_file, output_file)
        print(f"✓ Файл упакован: {packed_path}")
        print(f"  Размер оригинала: {test_file.stat().st_size} байт")
        print(f"  Размер упакованного: {packed_path.stat().st_size} байт\n")
    except Exception as e:
        print(f"✗ Ошибка: {e}\n")


def example_batch_processing():
    """Пример пакетной обработки"""
    print("=== Пример 5: Пакетная обработка ===\n")

    # Создаем несколько тестовых файлов
    temp_dir = Path("temp/batch_test")
    temp_dir.mkdir(parents=True, exist_ok=True)

    files_to_process = []
    
    for i in range(3):
        file_path = temp_dir / f"module_{i}.py"
        with open(file_path, 'w') as f:
            f.write(f"def module_{i}_function(): return {i}\n")
        files_to_process.append(file_path)
        print(f"Создан файл: {file_path}")

    print()

    # Пакетная обработка
    output_dir = temp_dir / "packed_output"
    processor = NPManagerBatchProcessor(aggressive=False)
    
    results = processor.process_batch(files_to_process, output_dir)
    summary = processor.get_summary()

    print(f"\nСуммарные результаты:")
    print(f"  Всего файлов: {summary['total']}")
    print(f"  Успешно: {summary['successful']}")
    print(f"  Ошибок: {summary['failed']}\n")


def example_protection_marker():
    """Пример генерации маркера защиты"""
    print("=== Пример 6: Маркер защиты ===\n")

    manager = NPManager()
    marker = manager.generate_protection_marker()

    print("Маркер защиты:")
    print(marker)
    print()


def example_mythical_names():
    """Пример использования мифических имен"""
    print("=== Пример 7: Мифические имена обфускации ===\n")

    from services import MythicalName

    print("Доступные мифические имена:")
    for name in MythicalName:
        print(f"  - {name.value}")

    print(f"\nВсего имен для обфускации: {len(list(MythicalName))}\n")


def example_system_package_masks():
    """Пример масок системных пакетов"""
    print("=== Пример 8: Маски системных пакетов ===\n")

    from services import SystemServiceMask

    print("Доступные маски системных пакетов:")
    for mask in SystemServiceMask:
        print(f"  - {mask.value}")

    print(f"\nВсего масок: {len(list(SystemServiceMask))}\n")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ NPMANAGER УПАКОВЩИКА")
    print("="*60 + "\n")

    try:
        example_basic_packing()
    except Exception as e:
        print(f"Ошибка в примере 1: {e}\n")

    try:
        example_aggressive_packing()
    except Exception as e:
        print(f"Ошибка в примере 2: {e}\n")

    try:
        example_factory_creation()
    except Exception as e:
        print(f"Ошибка в примере 3: {e}\n")

    try:
        example_file_packing()
    except Exception as e:
        print(f"Ошибка в примере 4: {e}\n")

    try:
        example_batch_processing()
    except Exception as e:
        print(f"Ошибка в примере 5: {e}\n")

    try:
        example_protection_marker()
    except Exception as e:
        print(f"Ошибка в примере 6: {e}\n")

    try:
        example_mythical_names()
    except Exception as e:
        print(f"Ошибка в примере 7: {e}\n")

    try:
        example_system_package_masks()
    except Exception as e:
        print(f"Ошибка в примере 8: {e}\n")

    print("="*60)
    print("Все примеры завершены!")
    print("="*60)
