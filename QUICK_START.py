"""
🚀 QUICK START GUIDE - Быстрый старт FullAPKProtector

Самый простой способ защитить APK в несколько строк кода
"""

from services import FullAPKProtector, APKProtectionPipeline
from pathlib import Path


# ==========================================
# СЦЕНАРИЙ 1: Защитить один APK
# ==========================================

def scenario_protect_single_apk():
    """Самый простой способ - защитить один APK файл"""
    
    print("\n📱 СЦЕНАРИЙ 1: Защита одного APK")
    print("="*50 + "\n")
    
    # Шаг 1: Создаем протектор
    protector = FullAPKProtector(aggressive=True)
    print("✓ Протектор создан")
    
    # Шаг 2: Защищаем APK
    apk_path = "temp/test.apk"
    
    # Создаем тестовый файл если его нет
    if not Path(apk_path).exists():
        Path(apk_path).parent.mkdir(parents=True, exist_ok=True)
        with open(apk_path, 'wb') as f:
            f.write(b"TEST_APK" * 100)
        print(f"✓ Создан тестовый APK: {apk_path}")
    
    try:
        protected_apk = protector.protect_apk_file(apk_path)
        print(f"✓ APK защищен: {protected_apk}\n")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


# ==========================================
# СЦЕНАРИЙ 2: Защитить несколько APK
# ==========================================

def scenario_protect_multiple_apks():
    """Защита нескольких APK файлов одновременно"""
    
    print("\n📱 СЦЕНАРИЙ 2: Защита нескольких APK")
    print("="*50 + "\n")
    
    protector = FullAPKProtector(aggressive=False)  # Быстрая обработка
    print("✓ Протектор создан (режим Light для скорости)\n")
    
    # Создаем список APK для обработки
    apk_list = []
    for i in range(2):
        apk_path = f"temp/apk_{i}.apk"
        Path(apk_path).parent.mkdir(parents=True, exist_ok=True)
        
        if not Path(apk_path).exists():
            with open(apk_path, 'wb') as f:
                f.write(f"APK_{i}".encode() * 100)
        
        apk_list.append(apk_path)
        print(f"  {i+1}. {apk_path}")
    
    print()
    
    # Защищаем все APK
    try:
        results = protector.protect_apk_batch(apk_list)
        
        print("РЕЗУЛЬТАТЫ:")
        for apk, result in results.items():
            if result['status'] == 'success':
                print(f"  ✓ {Path(apk).name} → {Path(result['output']).name}")
            else:
                print(f"  ❌ {Path(apk).name} → Ошибка: {result['error']}")
        
        print()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


# ==========================================
# СЦЕНАРИЙ 3: Использовать конвейер
# ==========================================

def scenario_use_pipeline():
    """Еще более простой способ - использовать конвейер"""
    
    print("\n📱 СЦЕНАРИЙ 3: Использование конвейера")
    print("="*50 + "\n")
    
    # Конвейер - это упрощенный интерфейс
    pipeline = APKProtectionPipeline()
    print("✓ Конвейер создан\n")
    
    # Создаем тестовый APK
    apk_path = "temp/pipeline_test.apk"
    Path(apk_path).parent.mkdir(parents=True, exist_ok=True)
    
    if not Path(apk_path).exists():
        with open(apk_path, 'wb') as f:
            f.write(b"PIPELINE_TEST" * 100)
        print(f"✓ Тестовый APK: {apk_path}\n")
    
    try:
        # Один вызов - и готово!
        protected = pipeline.process_apk(apk_path)
        print(f"✓ APK защищен через конвейер: {protected}\n")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


# ==========================================
# СЦЕНАРИЙ 4: Получить информацию о защите
# ==========================================

def scenario_get_protection_info():
    """Получить полную информацию о системе защиты"""
    
    print("\n📱 СЦЕНАРИЙ 4: Информация о защите")
    print("="*50 + "\n")
    
    protector = FullAPKProtector()
    
    # Статус
    status = protector.get_status()
    print("СТАТУС ПРОТЕКТОРА:")
    print(f"  Активен: {status['protector_active']}")
    print(f"  Режим: {status['protection_mode']}")
    print(f"  Компонентов инициализировано: {sum(1 for v in status['components_initialized'].values() if v)}\n")
    
    # Отчет
    report = protector.generate_protection_report()
    print("ОТЧЕТ БЕЗОПАСНОСТИ:")
    print(f"  Уровень: {report['protection_level']}")
    print(f"  Функций защиты: {report['total_features']}\n")
    
    print("ТОП-10 ФУНКЦИЙ ЗАЩИТЫ:")
    for i, feature in enumerate(report['security_features'][:10], 1):
        print(f"  {i:2}. {feature}")
    
    print()
    return True


# ==========================================
# СЦЕНАРИЙ 5: Выбрать режим защиты
# ==========================================

def scenario_choose_protection_mode():
    """Выбрать подходящий режим защиты"""
    
    print("\n📱 СЦЕНАРИЙ 5: Выбор режима защиты")
    print("="*50 + "\n")
    
    # Режим 1: Максимальная защита
    print("РЕЖИМ 1: AGGRESSIVE (Максимальная защита)")
    print("-" * 50)
    aggressive = FullAPKProtector(aggressive=True)
    report_agg = aggressive.generate_protection_report()
    print(f"  Уровень защиты: {report_agg['protection_level']}")
    print(f"  Функции: {report_agg['total_features']}")
    print(f"  Лучше для: Критичные приложения, приватные данные\n")
    
    # Режим 2: Быстрая обработка
    print("РЕЖИМ 2: LIGHT (Быстрая обработка)")
    print("-" * 50)
    light = FullAPKProtector(aggressive=False)
    report_light = light.generate_protection_report()
    print(f"  Уровень защиты: {report_light['protection_level']}")
    print(f"  Функции: {report_light['total_features']}")
    print(f"  Лучше для: Пакетная обработка, большое количество APK\n")
    
    print("РЕКОМЕНДАЦИЯ: Используйте aggressive=True для важных приложений\n")
    return True


# ==========================================
# СЦЕНАРИЙ 6: Обработка кода
# ==========================================

def scenario_protect_code():
    """Защитить исходный код"""
    
    print("\n📱 СЦЕНАРИЙ 6: Защита исходного кода")
    print("="*50 + "\n")
    
    protector = FullAPKProtector(aggressive=True)
    
    # Пример кода для защиты
    code = """
def login_user(username, password):
    db_connection = "server=prod.db.local"
    api_key = "sk_live_abc123def456"
    
    user = authenticate(username, password)
    return user
"""

    print("ИСХОДНЫЙ КОД:")
    print("-" * 50)
    print(code)
    
    try:
        protected_code = protector.protect_source_code(code)
        
        print("ЗАЩИЩЕННЫЙ КОД (первые 300 символов):")
        print("-" * 50)
        print(protected_code[:300])
        print("...")
        print()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


# ==========================================
# СЦЕНАРИЙ 7: Полный рабочий процесс
# ==========================================

def scenario_full_workflow():
    """Полный рабочий процесс: инициализация → обработка → проверка"""
    
    print("\n📱 СЦЕНАРИЙ 7: Полный рабочий процесс")
    print("="*50 + "\n")
    
    steps = [
        "1️⃣  Инициализация системы защиты",
        "2️⃣  Проверка компонентов",
        "3️⃣  Создание тестового APK",
        "4️⃣  Защита APK",
        "5️⃣  Генирование отчета",
        "6️⃣  Проверка результата"
    ]
    
    for step in steps:
        print(f"  {step}")
    
    print("\n" + "-"*50 + "\n")
    
    # Выполняем все шаги
    try:
        # Шаг 1-2
        protector = FullAPKProtector(aggressive=True)
        status = protector.get_status()
        print(f"✓ Протектор активен ({len(status['components_initialized'])} компонентов)\n")
        
        # Шаг 3
        test_apk = "temp/workflow_test.apk"
        Path(test_apk).parent.mkdir(parents=True, exist_ok=True)
        with open(test_apk, 'wb') as f:
            f.write(b"WORKFLOW_TEST" * 100)
        print(f"✓ Тестовый APK создан\n")
        
        # Шаг 4
        protected = protector.protect_apk_file(test_apk)
        print(f"✓ APK защищен: {protected}\n")
        
        # Шаг 5
        report = protector.generate_protection_report()
        print(f"✓ Отчет создан")
        print(f"  • Уровень защиты: {report['protection_level']}")
        print(f"  • Функции: {report['total_features']}\n")
        
        # Шаг 6
        if Path(protected).exists():
            size = Path(protected).stat().st_size
            print(f"✓ Результат проверен")
            print(f"  • Размер: {size} байт\n")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}\n")
        return False


# ==========================================
# РУНЕР - Запуск всех сценариев
# ==========================================

def run_all_scenarios():
    """Запустить все сценарии"""
    
    print("\n" + "🔐"*25)
    print("QUICK START GUIDE - ВСЕ СЦЕНАРИИ")
    print("🔐"*25)
    
    scenarios = [
        ("Защита одного APK", scenario_protect_single_apk),
        ("Защита нескольких APK", scenario_protect_multiple_apks),
        ("Использование конвейера", scenario_use_pipeline),
        ("Информация о защите", scenario_get_protection_info),
        ("Выбор режима защиты", scenario_choose_protection_mode),
        ("Защита кода", scenario_protect_code),
        ("Полный рабочий процесс", scenario_full_workflow),
    ]
    
    results = []
    
    for name, scenario_func in scenarios:
        try:
            result = scenario_func()
            results.append((name, "✓"))
        except Exception as e:
            print(f"❌ Ошибка в '{name}': {e}\n")
            results.append((name, "✗"))
    
    # Итоговый отчет
    print("\n" + "="*50)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*50 + "\n")
    
    for name, status in results:
        symbol = "✓" if status == "✓" else "✗"
        print(f"  {symbol} {name}")
    
    print("\n" + "="*50)
    print(f"ЗАВЕРШЕНО: {sum(1 for _, s in results if s == '✓')}/{len(results)} сценариев")
    print("="*50 + "\n")


# ==========================================
# ШПАРГАЛКА
# ==========================================

def show_cheatsheet():
    """Показать шпаргалку"""
    
    print("\n" + "📝"*20)
    print("ШПАРГАЛКА - САМЫЕ НУЖНЫЕ КОМАНДЫ")
    print("📝"*20 + "\n")
    
    cheatsheet = """
🚀 САМЫЙ ПРОСТОЙ СПОСОБ:
    from services import FullAPKProtector
    protector = FullAPKProtector()
    protected = protector.protect_apk_file("app.apk")

💨 БЫСТРЫЙ КОНВЕЙЕР:
    from services import APKProtectionPipeline
    pipeline = APKProtectionPipeline()
    protected = pipeline.process_apk("app.apk")

📱 ЗАЩИТА НЕСКОЛЬКИХ:
    results = protector.protect_apk_batch(["app1.apk", "app2.apk"])

📊 ИНФОРМАЦИЯ:
    report = protector.generate_protection_report()
    status = protector.get_status()

💻 ЗАЩИТА КОДА:
    protected_code = protector.protect_source_code(source_code)

⚙️ ВЫБОР РЕЖИМА:
    # Максимальная защита (медленнее)
    protector = FullAPKProtector(aggressive=True)
    
    # Быстрая обработка (меньше защиты)
    protector = FullAPKProtector(aggressive=False)

📂 РЕЗУЛЬТАТЫ:
    output/
    ├── protected_app_*.apk       ← Защищенный APK
    ├── protected_app_*_key.txt   ← Ключи
    ├── logs/                     ← Логи
    └── reports/                  ← Отчеты
"""
    
    print(cheatsheet)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "cheatsheet":
        show_cheatsheet()
    else:
        run_all_scenarios()
        print("\n💡 Совет: Запустите 'python QUICK_START.py cheatsheet' для шпаргалки\n")
