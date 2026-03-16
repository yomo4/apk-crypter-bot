"""
Пример маскировки под системный сервис tech.framework.helper
Демонстрирует как скрыть приложение под системный компонент Android
"""

from pathlib import Path
from services import NPManager, SystemServiceMask, TechFrameworkMasker, AndroidSystemMasker


def demonstrate_tech_framework_masking():
    """Демонстрация маскировки под tech.framework.helper"""
    
    print("="*70)
    print("МАСКИРОВКА ПОД СИСТЕМНЫЙ СЕРВИС: tech.framework.helper")
    print("="*70)
    print()

    # Создаем критичный код
    sensitive_code = """
import os
import json
from pathlib import Path

class FrameworkHelper:
    \"\"\"Системный помощник фреймворка\"\"\"
    
    def __init__(self):
        self.cache = {}
        self.config = {}
    
    def load_configuration(self):
        \"\"\"Загружает конфигурацию системы\"\"\"
        config_file = Path("/system/framework/config.json")
        if config_file.exists():
            with open(config_file, 'r') as f:
                self.config = json.load(f)
        return self.config
    
    def initialize_services(self):
        \"\"\"Инициализирует системные сервисы\"\"\"
        self.load_configuration()
        return True
    
    def process_framework_event(self, event_data):
        \"\"\"Обрабатывает события фреймворка\"\"\"
        cache_key = hash(str(event_data))
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        result = self._process(event_data)
        self.cache[cache_key] = result
        return result
    
    def _process(self, data):
        \"\"\"Внутренняя обработка\"\"\"
        return {"status": "processed", "data": data}

def main():
    helper = FrameworkHelper()
    helper.initialize_services()
    print("Framework helper initialized successfully")

if __name__ == "__main__":
    main()
"""

    print("1. ИСХОДНЫЙ КОД")
    print("-" * 70)
    print(sensitive_code)
    print()

    # Создаем NPManager с маскировкой под tech.framework.helper
    print("2. СОЗДАНИЕ МЕНЕДЖЕРА МАСКИРОВКИ")
    print("-" * 70)
    manager = NPManager(package_name="tech.framework.helper")
    
    print(f"✓ Пакет: {manager.package.package_name}")
    print(f"✓ Версия защиты: {manager.package.version}")
    print(f"✓ Автор: {manager.package.author}")
    print(f"✓ Функция защиты: {manager.package.function}")
    print(f"✓ Время защиты: {manager.package.protect_time}")
    print()

    # Упаковываем код с агрессивной защитой
    print("3. УПАКОВКА КОДА С МАСКИРОВКОЙ")
    print("-" * 70)
    print("Применяемые техники обфускации:")
    print("  1. Маскировка пакета -> tech.framework.helper")
    print("  2. Переименование функций -> мифические имена")
    print("  3. Добавление контроля потока управления (CFO)")
    print("  4. Фейковые переменные и XOR обфускация")
    print("  5. Anti-analysis проверки (timing, memory, stack)")
    print("  6. Динамическое кодирование критичных строк")
    print("  7. Фейковые системные методы")
    print("  8. Мусорный код для запутывания")
    print()

    packed_code = manager.pack(sensitive_code, aggressive=True)

    print("4. УПАКОВАННЫЙ КОД (первые 600 символов)")
    print("-" * 70)
    print(packed_code[:600])
    print("\n... (код продолжается) \n")

    # Показываем маркер защиты
    print("5. МАРКЕР ЗАЩИТЫ")
    print("-" * 70)
    marker = manager.generate_protection_marker()
    print(marker)

    # Показываем отчет об упаковке
    print("6. ОТЧЕТ ОБ УПАКОВКЕ")
    print("-" * 70)
    report = manager.get_pack_report()
    
    print(f"Пакет: {report['package_name']}")
    print(f"Версия: {report['version']}")
    print(f"Автор: {report['author']}")
    print(f"Обфускировано функций: {report['obfuscation_map'].get('names', {})}")
    print(f"Мифических имен: {len(report['mythical_names'])}")
    print(f"Фейковых переменных: {len(report['fake_variables'])}")
    print()

    print("7. ПЕРЕМЕННЫЕ ДЛЯ ОБФУСКАЦИИ")
    print("-" * 70)
    print("Мифические имена функций:")
    for original, mythical in list(report['mythical_names'].items())[:5]:
        print(f"  {original} -> {mythical}")
    print()

    print("Фейковые переменные (для запутывания):")
    for var_name, value in list(report['fake_variables'].items())[:5]:
        print(f"  {var_name} = {value}")
    print()

    # Демонстрация сохранения
    print("8. СОХРАНЕНИЕ УПАКОВАННОГО КОДА")
    print("-" * 70)
    output_path = Path("temp/tech_framework_masked.py")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(packed_code)
    
    print(f"✓ Код сохранен: {output_path}")
    print(f"✓ Размер оригинала: {len(sensitive_code)} байт")
    print(f"✓ Размер упакованного: {len(packed_code)} байт")
    print(f"✓ Увеличение (за счет защиты): {len(packed_code) - len(sensitive_code)} байт")
    print()

    # Показываем все доступные маски
    print("9. ДОСТУПНЫЕ МАСКИ СИСТЕМНЫХ ПАКЕТОВ")
    print("-" * 70)
    for i, mask in enumerate(SystemServiceMask, 1):
        print(f"{i}. {mask.value}")
    print()

    # Рекомендации по использованию
    print("10. РЕКОМЕНДАЦИИ ПО ИСПОЛЬЗОВАНИЮ")
    print("-" * 70)
    print("""
    ✓ Используйте для критичного кода, который должен избежать анализа
    ✓ Комбинируйте с другими защитами (AES шифрование, Rate limiting и т.д.)
    ✓ Агрессивная маскировка обеспечивает максимальную защиту
    ✓ Легкая маскировка быстрее, но менее защищена
    ✓ Указывайте правильный package_name для реалистичности
    ✓ Маркер защиты должен быть сложен для удаления
    ✓ Проверяйте целостность кода после упаковки
    """)

    print("="*70)
    print("МАСКИРОВКА ЗАВЕРШЕНА УСПЕШНО")
    print("="*70)


def demonstrate_all_masks():
    """Демонстрирует все доступные маски"""
    print("\n" + "="*70)
    print("ВСЕ ДОСТУПНЫЕ МАСКИ СИСТЕМНЫХ ПАКЕТОВ")
    print("="*70 + "\n")

    masks = [mask.value for mask in SystemServiceMask]
    
    for i, mask in enumerate(masks, 1):
        print(f"{i}. {mask}")
        
        # Создаем менеджер с этой маской
        manager = NPManager(package_name=mask)
        print(f"   Генерируемые имена функций: {list(manager.package.mythical_names.values())[:3]}")
        print()

    print("Совет: Выбирайте маску которая лучше всего соответствует контексту приложения")
    print()


def demonstrate_aggressive_vs_light():
    """Сравнение агрессивной и легкой маскировки"""
    print("\n" + "="*70)
    print("СРАВНЕНИЕ: АГРЕССИВНАЯ vs ЛЕГКАЯ МАСКИРОВКА")
    print("="*70 + "\n")

    simple_code = "def calculate(): return 10 + 20"

    # Легкая маскировка
    print("ЛЕГКАЯ МАСКИРОВКА:")
    print("-" * 70)
    light_manager = NPManager(package_name="tech.framework.helper")
    light_packed = light_manager.pack(simple_code, aggressive=False)
    print(f"Размер: {len(light_packed)} байт")
    print(f"Первые 200 символов:\n{light_packed[:200]}\n")

    # Агрессивная маскировка
    print("АГРЕССИВНАЯ МАСКИРОВКА:")
    print("-" * 70)
    aggressive_manager = NPManager(package_name="tech.framework.helper")
    aggressive_packed = aggressive_manager.pack(simple_code, aggressive=True)
    print(f"Размер: {len(aggressive_packed)} байт")
    print(f"Первые 200 символов:\n{aggressive_packed[:200]}\n")

    print("Сравнение:")
    print(f"  Оригинал: {len(simple_code)} байт")
    print(f"  Легкая защита: {len(light_packed)} байт (увеличение в {len(light_packed)/len(simple_code):.1f}x)")
    print(f"  Агрессивная защита: {len(aggressive_packed)} байт (увеличение в {len(aggressive_packed)/len(simple_code):.1f}x)")
    print()


def demonstrate_tech_framework_masker_class():
    """Демонстрация специализированного класса TechFrameworkMasker"""
    print("\n" + "="*70)
    print("СПЕЦИАЛИЗИРОВАННЫЙ КЛАСС: TechFrameworkMasker")
    print("="*70 + "\n")

    code = """
def get_system_info():
    import platform
    return {
        "system": platform.system(),
        "version": platform.version(),
    }

def main():
    info = get_system_info()
    print(f"System: {info}")

if __name__ == "__main__":
    main()
"""

    print("1. СОЗДАНИЕ МАСКИРОВЩИКА")
    print("-" * 70)
    masker = TechFrameworkMasker()
    
    package_info = masker.get_package_info()
    print(f"Пакет: {package_info['package_name']}")
    print(f"Версия: {package_info['version']}")
    print(f"Автор: {package_info['author']}")
    print(f"Функция: {package_info['function']}")
    print()

    print("2. МАСКИРОВКА ОБЫЧНОГО КОДА")
    print("-" * 70)
    masked_code = masker.mask_code(code, aggressive=True)
    print(f"Упакованный код (первые 300 символов):")
    print(masked_code[:300])
    print("...\n")

    print("3. СОЗДАНИЕ ПОЛНОГО ЗАМАСКИРОВАННОГО ПАКЕТА")
    print("-" * 70)
    full_package = masker.create_masked_package(
        code, 
        include_service_init=True,
        aggressive=True
    )
    print(f"Полный пакет размер: {len(full_package)} байт")
    print(f"Первые 400 символов:\n{full_package[:400]}\n")

    print("4. ОТЧЕТ О МАСКИРОВКЕ")
    print("-" * 70)
    report = masker.get_masking_report()
    print(f"Тип маскировки: {report['masking_type']}")
    print(f"Пакет: {report['package_name']}")
    print(f"Системный сервис: {report['system_service']}")
    print(f"Описание: {report['description']}")
    print()

    print("5. ЗАГОЛОВОК ЗАЩИТЫ")
    print("-" * 70)
    header = masker.get_protection_header()
    print(header)


def demonstrate_android_system_masker():
    """Демонстрация универсального Android маскировщика"""
    print("\n" + "="*70)
    print("УНИВЕРСАЛЬНЫЙ ANDROID МАСКИРОВЩИК")
    print("="*70 + "\n")

    code = "def service(): return 'running'"

    print("1. МАСКИРОВКА ПОД РАЗЛИЧНЫЕ СИСТЕМНЫЕ СЕРВИСЫ")
    print("-" * 70)

    # tech.framework.helper
    print("\n► tech.framework.helper")
    result1 = AndroidSystemMasker.mask_as_tech_framework(code, aggressive=False)
    print(f"  Размер: {len(result1)} байт")

    # android.system.service
    print("\n► android.system.service")
    result2 = AndroidSystemMasker.mask_as_android_system(code, aggressive=False)
    print(f"  Размер: {len(result2)} байт")

    # com.android.internal.util
    print("\n► com.android.internal.util")
    result3 = AndroidSystemMasker.mask_as_internal_util(code, aggressive=False)
    print(f"  Размер: {len(result3)} байт")

    # framework.base.service
    print("\n► framework.base.service")
    result4 = AndroidSystemMasker.mask_as_framework_base(code, aggressive=False)
    print(f"  Размер: {len(result4)} байт")
    print()

    print("2. СРАВНЕНИЕ РАЗМЕРОВ")
    print("-" * 70)
    results = {
        "tech.framework.helper": len(result1),
        "android.system.service": len(result2),
        "com.android.internal.util": len(result3),
        "framework.base.service": len(result4),
    }

    for service, size in sorted(results.items(), key=lambda x: x[1]):
        print(f"  {service:30} {size:5} байт")
    print()


if __name__ == "__main__":
    # Основная демонстрация маскировки
    demonstrate_tech_framework_masking()
    
    # Все доступные маски
    demonstrate_all_masks()
    
    # Сравнение уровней защиты
    demonstrate_aggressive_vs_light()

    # Специализированный класс TechFrameworkMasker
    demonstrate_tech_framework_masker_class()

    # Универсальный Android маскировщик
    demonstrate_android_system_masker()

    print("\n" + "="*70)
    print("ВСЕ ДЕМОНСТРАЦИИ ЗАВЕРШЕНЫ")
    print("="*70)
