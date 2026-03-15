"""
NPManager-style obfuscator
Техники: запутывание имен, динамическая расшифровка, маскировка под системный сервис
"""
import random
import string
from datetime import datetime


class NPManager:
    """Упаковщик в стиле NPManager"""
    
    # Мифические существа для имен
    MYTHICAL_NAMES = [
        "gorila", "chimera", "fenrir", "wyvern", "hydra", "kraken",
        "phoenix", "dragon", "griffin", "basilisk", "cerberus", "sphinx",
        "minotaur", "medusa", "pegasus", "unicorn", "leviathan", "behemoth"
    ]
    
    # Системные имена пакетов для маскировки
    SYSTEM_PACKAGES = [
        "tech.framework.helper",
        "android.system.service",
        "com.android.internal.util",
        "system.core.manager",
        "framework.base.service"
    ]
    
    def __init__(self):
        self.used_names = set()
        self.string_mappings = {}
        self.version = "3.0.61"
        self.author = "CryptoAnon"
        
    def get_mythical_name(self) -> str:
        """Возвращает случайное имя мифического существа"""
        available = [n for n in self.MYTHICAL_NAMES if n not in self.used_names]
        if not available:
            # Если все имена использованы, добавляем суффикс
            name = random.choice(self.MYTHICAL_NAMES) + str(random.randint(1, 99))
        else:
            name = random.choice(available)
        self.used_names.add(name)
        return name
    
    def get_system_package(self) -> str:
        """Возвращает системное имя пакета"""
        return random.choice(self.SYSTEM_PACKAGES)
    
    def string_to_short_array(self, text: str) -> str:
        """Конвертирует строку в массив short[] для динамической расшифровки"""
        shorts = [str(ord(c)) for c in text]
        return "{" + ", ".join(shorts) + "}"
    
    def generate_string_decoder(self) -> str:
        """Генерирует метод расшифровки строк из short[]"""
        decoder_name = self.get_mythical_name()
        return f'''
    private static String {decoder_name}(short[] data) {{
        char[] chars = new char[data.length];
        for (int i = 0; i < data.length; i++) {{
            chars[i] = (char) data[i];
        }}
        return new String(chars);
    }}''', decoder_name
    
    def obfuscate_string(self, text: str, decoder_name: str) -> str:
        """Обфусцирует строку через short[] массив"""
        short_array = self.string_to_short_array(text)
        return f'{decoder_name}(new short[] {short_array})'
    
    def generate_control_flow_obfuscation(self) -> str:
        """Генерирует запутывание потока управления"""
        var1 = self.get_mythical_name()
        var2 = self.get_mythical_name()
        var3 = self.get_mythical_name()
        
        return f'''
    private int {var1} = {random.randint(1000, 9999)};
    private int {var2} = {random.randint(1000, 9999)};
    
    private boolean {var3}() {{
        int x = {var1} ^ {var2};
        for (int i = 0; i < 100; i++) {{
            x = (x * {random.randint(2, 9)}) % {random.randint(1000, 9999)};
            if (x < 0) x = -x;
        }}
        return x > 0;
    }}'''
    
    def generate_fake_system_methods(self) -> str:
        """Генерирует фейковые системные методы для маскировки"""
        methods = []
        for _ in range(3):
            name = self.get_mythical_name()
            method = f'''
    private void {name}SystemService() {{
        // Fake system service call
        try {{
            Thread.sleep({random.randint(10, 50)});
        }} catch (Exception e) {{}}
    }}'''
            methods.append(method)
        return '\n'.join(methods)
    
    def generate_protection_marker(self) -> str:
        """Генерирует маркер защиты NPManager"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        return f'''
    // ===== Protected by NPManager =====
    // Author: {self.author}
    // Function: Control Flow Obfuscation
    // Version: {self.version}
    // ProtectTime: {timestamp}
    // ===================================
'''
    
    def wrap_method_with_obfuscation(self, method_code: str) -> str:
        """Оборачивает метод в защитный слой"""
        check_var = self.get_mythical_name()
        return f'''
        // Control flow obfuscation
        int {check_var} = {random.randint(1, 100)};
        if ({check_var} > 0) {{
            {method_code}
        }}'''
    
    def generate_anti_analysis_checks(self) -> str:
        """Генерирует проверки против анализа"""
        check1 = self.get_mythical_name()
        check2 = self.get_mythical_name()
        check3 = self.get_mythical_name()
        
        return f'''
    private boolean {check1}() {{
        // Check 1: Timing attack detection
        long start = System.currentTimeMillis();
        int x = 0;
        for (int i = 0; i < 1000; i++) {{
            x += i;
        }}
        long end = System.currentTimeMillis();
        return (end - start) < 100;
    }}
    
    private boolean {check2}() {{
        // Check 2: Memory analysis detection
        Runtime runtime = Runtime.getRuntime();
        long maxMemory = runtime.maxMemory();
        long totalMemory = runtime.totalMemory();
        return (maxMemory - totalMemory) > 1024 * 1024 * 10;
    }}
    
    private boolean {check3}() {{
        // Check 3: Stack trace analysis
        StackTraceElement[] stack = Thread.currentThread().getStackTrace();
        return stack.length < 50;
    }}
    
    private boolean {self.get_mythical_name()}Verify() {{
        return {check1}() && {check2}() && {check3}();
    }}'''
