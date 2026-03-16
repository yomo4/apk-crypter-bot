"""
Примеры использования FullAPKProtector - полного интегратора защиты
Демонстрирует как работать со всем защитным слоем вместе
"""

import logging
from pathlib import Path
from services import FullAPKProtector, APKProtectionPipeline

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def example_simple_apk_protection():
    """Пример 1: Простая защита одного APK файла"""
    print("\n" + "="*70)
    print("ПРИМЕР 1: ПРОСТАЯ ЗАЩИТА APK")
    print("="*70 + "\n")

    # Создаем test APK для примера
    test_apk = Path("temp/test.apk")
    test_apk.parent.mkdir(parents=True, exist_ok=True)
    
    if not test_apk.exists():
        # Создаем фейковый APK для демонстрации
        with open(test_apk, 'wb') as f:
            f.write(b"TEST_APK_CONTENT" * 100)
        print(f"✓ Создан тестовый APK: {test_apk}\n")
    
    # Инициализируем протектор
    protector = FullAPKProtector(aggressive=True)
    
    try:
        # Защищаем APK
        protected_apk = protector.protect_apk_file(str(test_apk))
        print(f"\n✓ Защищенный APK: {protected_apk}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


def example_light_protection():
    """Пример 2: Легкая защита (быстрая обработка)"""
    print("\n" + "="*70)
    print("ПРИМЕР 2: ЛЕГКАЯ ЗАЩИТА (БЫСТРАЯ ОБРАБОТКА)")
    print("="*70 + "\n")

    test_apk = Path("temp/light_test.apk")
    test_apk.parent.mkdir(parents=True, exist_ok=True)
    
    if not test_apk.exists():
        with open(test_apk, 'wb') as f:
            f.write(b"LIGHT_APK" * 50)
    
    # Легкая защита (aggressive=False)
    protector = FullAPKProtector(aggressive=False)
    
    try:
        protected_apk = protector.protect_apk_file(str(test_apk))
        print(f"\n✓ APK защищен в облегченном режиме: {protected_apk}")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


def example_batch_protection():
    """Пример 3: Пакетная защита нескольких APK"""
    print("\n" + "="*70)
    print("ПРИМЕР 3: ПАКЕТНАЯ ЗАЩИТА")
    print("="*70 + "\n")

    # Создаем несколько тестовых APK
    apk_list = []
    for i in range(3):
        apk_file = Path(f"temp/batch_test_{i}.apk")
        apk_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not apk_file.exists():
            with open(apk_file, 'wb') as f:
                f.write(f"APK_{i}_CONTENT".encode() * 30)
        
        apk_list.append(str(apk_file))
        print(f"  - Создан APK: {apk_file}")
    
    print()
    
    protector = FullAPKProtector(aggressive=True)
    
    try:
        results = protector.protect_apk_batch(apk_list)
        
        print("\nРЕЗУЛЬТАТЫ ПАКЕТНОЙ ОБРАБОТКИ:")
        print("-" * 70)
        for apk, result in results.items():
            status = result['status']
            if status == 'success':
                print(f"✓ {Path(apk).name}: {result['output']}")
            else:
                print(f"✗ {Path(apk).name}: Ошибка - {result['error']}")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


def example_protection_report():
    """Пример 4: Генерирование отчета защиты"""
    print("\n" + "="*70)
    print("ПРИМЕР 4: ОТЧЕТ ЗАЩИТЫ")
    print("="*70 + "\n")

    protector = FullAPKProtector(aggressive=True)
    
    # Получение отчета
    report = protector.generate_protection_report()
    
    print("КОМПОНЕНТЫ ЗАЩИТЫ:")
    print("-" * 70)
    for component, status in report['components'].items():
        print(f"  ✓ {component}: {status}")
    
    print("\nОСНОВНЫЕ ОСОБЕННОСТИ ЗАЩИТЫ:")
    print("-" * 70)
    for i, feature in enumerate(report['security_features'], 1):
        print(f"  {i:2}. {feature}")
    
    print()


def example_protector_status():
    """Пример 5: Получение статуса протектора"""
    print("\n" + "="*70)
    print("ПРИМЕР 5: СТАТУС ПРОТЕКТОРА")
    print("="*70 + "\n")

    protector = FullAPKProtector(aggressive=True)
    
    status = protector.get_status()
    
    print("СТАТУС СИСТЕМЫ ЗАЩИТЫ:")
    print("-" * 70)
    print(f"Протектор активен: {status['protector_active']}")
    print(f"Режим защиты: {status['protection_mode']}")
    print(f"Выходная директория: {status['output_directory']}")
    print(f"Временная директория: {status['temp_directory']}")
    
    print("\nИНИЦИАЛИЗИРОВАННЫЕ КОМПОНЕНТЫ:")
    print("-" * 70)
    for component, initialized in status['components_initialized'].items():
        status_str = "✓ инициализирован" if initialized else "✗ ошибка"
        print(f"  {component:30} {status_str}")
    
    print()


def example_pipeline():
    """Пример 6: Использование конвейера обработки"""
    print("\n" + "="*70)
    print("ПРИМЕР 6: КОНВЕЙЕР ОБРАБОТКИ")
    print("="*70 + "\n")

    # Создаем тестовый APK
    test_apk = Path("temp/pipeline_test.apk")
    test_apk.parent.mkdir(parents=True, exist_ok=True)
    
    if not test_apk.exists():
        with open(test_apk, 'wb') as f:
            f.write(b"PIPELINE_APK_TEST" * 40)
        print(f"✓ Создан тестовый APK: {test_apk}\n")
    
    # Инициализируем конвейер
    pipeline = APKProtectionPipeline()
    
    print("Информация о конвейере:")
    pipeline_status = pipeline.get_status()
    print(f"  Статус: {'Активен' if pipeline_status['protector_active'] else 'Неактивен'}")
    print(f"  Режим: {pipeline_status['protection_mode']}\n")
    
    try:
        # Обработка APK через конвейер
        protected = pipeline.process_apk(str(test_apk))
        print(f"\n✓ APK обработан конвейером: {protected}")
        
        # Получение отчета от конвейера
        report = pipeline.get_report()
        print(f"\nКомпоненты защиты в конвейере:")
        for component, status in report['components'].items():
            print(f"  ✓ {component}: {status}")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


def example_source_code_protection():
    """Пример 7: Защита исходного кода"""
    print("\n" + "="*70)
    print("ПРИМЕР 7: ЗАЩИТА ИСХОДНОГО КОДА")
    print("="*70 + "\n")

    # Исходный код для защиты
    source_code = '''
def sensitive_function():
    """Чувствительная функция"""
    api_key = "secret-api-key-12345"
    return api_key

def process_user_data(user_id, data):
    """Обработка данных пользователя"""
    result = {}
    result['user_id'] = user_id
    result['processed'] = True
    return result

def main():
    func_result = sensitive_function()
    print(f"Результат: {func_result}")

if __name__ == "__main__":
    main()
'''

    print("ИСХОДНЫЙ КОД:")
    print("-" * 70)
    print(source_code)
    
    # Инициализируем протектор
    protector = FullAPKProtector(aggressive=True)
    
    print("\nЗАЩИЩАЮЩИЕ ТЕХНИКИ:")
    print("-" * 70)
    print("  1. Обфускация переменных и функций")
    print("  2. Кодирование строк")
    print("  3. Маскировка под tech.framework.helper")
    print("  4. Добавление anti-analysis проверок")
    print("  5. Добавление мусорного кода")
    print()
    
    try:
        protected_code = protector.protect_source_code(source_code)
        
        print("ЗАЩИЩЕННЫЙ КОД (первые 500 символов):")
        print("-" * 70)
        print(protected_code[:500])
        print("...\n")
    
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")


def example_complete_workflow():
    """Пример 8: Полный рабочий процесс"""
    print("\n" + "="*70)
    print("ПРИМЕР 8: ПОЛНЫЙ РАБОЧИЙ ПРОЦЕСС")
    print("="*70 + "\n")

    print("ЭТАПЫ:")
    print("-" * 70)
    
    # Этап 1: Инициализация
    print("1️⃣  Инициализация системы защиты...")
    protector = FullAPKProtector(aggressive=True)
    print("   ✓ Инициализирована\n")
    
    # Этап 2: Проверка статуса
    print("2️⃣  Проверка статуса...")
    status = protector.get_status()
    print(f"   ✓ Все компоненты инициализированы\n")
    
    # Этап 3: Получение информации о защите
    print("3️⃣  Получение информации о защите...")
    report = protector.generate_protection_report()
    print(f"   ✓ Уровень защиты: {report['protection_level']}")
    print(f"   ✓ Компонентов: {len(report['components'])}\n")
    
    # Этап 4: Подготовка к защите APK
    print("4️⃣  Подготовка тестового APK...")
    test_apk = Path("temp/complete_workflow.apk")
    test_apk.parent.mkdir(parents=True, exist_ok=True)
    with open(test_apk, 'wb') as f:
        f.write(b"COMPLETE_WORKFLOW_APK" * 50)
    print(f"   ✓ APK готов: {test_apk}\n")
    
    # Этап 5: Защита
    print("5️⃣  Защита APK...")
    try:
        protected = protector.protect_apk_file(str(test_apk))
        print(f"   ✓ APK защищен: {protected}\n")
    except Exception as e:
        print(f"   ❌ Ошибка защиты: {e}\n")
    
    print("="*70)
    print("РАБОЧИЙ ПРОЦЕСС ЗАВЕРШЕН")
    print("="*70)


if __name__ == "__main__":
    print("\n" + "🔐"*35)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ FullAPKProtector")
    print("🔐"*35)

    try:
        example_simple_apk_protection()
    except Exception as e:
        print(f"Ошибка в примере 1: {e}\n")

    try:
        example_light_protection()
    except Exception as e:
        print(f"Ошибка в примере 2: {e}\n")

    try:
        example_batch_protection()
    except Exception as e:
        print(f"Ошибка в примере 3: {e}\n")

    try:
        example_protection_report()
    except Exception as e:
        print(f"Ошибка в примере 4: {e}\n")

    try:
        example_protector_status()
    except Exception as e:
        print(f"Ошибка в примере 5: {e}\n")

    try:
        example_pipeline()
    except Exception as e:
        print(f"Ошибка в примере 6: {e}\n")

    try:
        example_source_code_protection()
    except Exception as e:
        print(f"Ошибка в примере 7: {e}\n")

    try:
        example_complete_workflow()
    except Exception as e:
        print(f"Ошибка в примере 8: {e}\n")

    print("\n" + "="*70)
    print("ВСЕ ПРИМЕРЫ ЗАВЕРШЕНЫ")
    print("="*70)
