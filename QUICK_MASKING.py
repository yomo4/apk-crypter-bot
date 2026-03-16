"""
Быстрая маскировка под tech.framework.helper
Простейший способ замаскировать код под системный сервис
"""

from pathlib import Path
from services import TechFrameworkMasker, AndroidSystemMasker


def quick_mask_code(code: str, aggressive: bool = True) -> str:
    """
    Быстро маскирует код под tech.framework.helper
    
    Args:
        code: Исходный Python код
        aggressive: Агрессивная защита (по умолчанию да)
    
    Returns:
        Замаскированный код
    
    Пример:
        masked = quick_mask_code("def hello(): print('world')")
        print(masked)
    """
    masker = TechFrameworkMasker()
    return masker.create_masked_package(code, aggressive=aggressive)


def quick_mask_file(file_path, output_path=None, aggressive=True):
    """
    Быстро маскирует Python файл
    
    Args:
        file_path: Путь к исходному файлу
        output_path: Путь для сохранения (опционально)
        aggressive: Уровень защиты
    
    Returns:
        Путь к замаскированному файлу
    
    Пример:
        quick_mask_file("main.py", "main_masked.py")
    """
    masker = TechFrameworkMasker()
    return masker.mask_file(Path(file_path), Path(output_path) if output_path else None, aggressive)


def quick_show_masking_info():
    """Показывает информацию о маскировке"""
    masker = TechFrameworkMasker()
    info = masker.get_package_info()
    
    print("="*60)
    print("МАСКИРОВКА ПОД СИСТЕМА СЕРВИС")
    print("="*60)
    print(f"Пакет: {info['package_name']}")
    print(f"Версия: {info['version']}")
    print(f"Автор: {info['author']}")
    print(f"Функция: {info['function']}")
    print(f"Описание: {info['description']}")
    print("="*60)
    print()


# ============================================================================
# Примеры быстрого использования
# ============================================================================

if __name__ == "__main__":
    print("\nПРИМЕР 1: Быстрая маскировка встроенного кода")
    print("-" * 60)
    
    code = """
def main():
    print("Hello from Framework Helper")
    return True

if __name__ == "__main__":
    main()
"""
    
    print("Исходный код:")
    print(code)
    print()
    
    masked = quick_mask_code(code, aggressive=True)
    print("Маскированный код (первые 400 символов):")
    print(masked[:400])
    print("...\n")

    print("\nПРИМЕР 2: Информация о маскировке")
    print("-" * 60)
    quick_show_masking_info()

    print("\nПРИМЕР 3: Мгновенная маскировка с файла")
    print("-" * 60)
    
    # Создаем тестовый файл
    test_file = Path("temp/quick_test.py")
    test_file.parent.mkdir(exist_ok=True)
    
    with open(test_file, 'w') as f:
        f.write("def test(): return 42\n")
    
    print(f"Создан тестовый файл: {test_file}")
    
    # Маскируем его
    try:
        masked_file = quick_mask_file(test_file)
        print(f"Замаскирован как: {masked_file}")
        print(f"Размер оригинала: {test_file.stat().st_size} байт")
        print(f"Размер маскированного: {masked_file.stat().st_size} байт\n")
    except Exception as e:
        print(f"Ошибка: {e}\n")

    print("\nПРИМЕР 4: Использование других системных масок")
    print("-" * 60)
    
    simple_code = "def api_call(): return 'data'"
    
    print("Маскировка под разные сервисы:")
    print(f"  1. tech.framework.helper: {len(AndroidSystemMasker.mask_as_tech_framework(simple_code))} байт")
    print(f"  2. android.system.service: {len(AndroidSystemMasker.mask_as_android_system(simple_code))} байт")
    print(f"  3. com.android.internal.util: {len(AndroidSystemMasker.mask_as_internal_util(simple_code))} байт")
    print(f"  4. framework.base.service: {len(AndroidSystemMasker.mask_as_framework_base(simple_code))} байт")
    print()

    print("\n" + "="*60)
    print("БЫСТРАЯ МАСКИРОВКА ЗАВЕРШЕНА!")
    print("="*60)
    print("\nДля использования в своем коде:")
    print("  from QUICK_MASKING import quick_mask_code, quick_mask_file")
    print("  masked_code = quick_mask_code(your_code)")
    print("  masked_file = quick_mask_file('input.py', 'output_masked.py')")
