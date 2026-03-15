import random
import string
import base64


class CodeObfuscator:
    """Обфускатор для Java кода"""
    
    def __init__(self):
        self.string_key = random.randint(1, 255)
        self.class_names = {}
    
    def obfuscate_string(self, text: str) -> str:
        """XOR обфускация строки"""
        encrypted = bytes([b ^ self.string_key for b in text.encode()])
        return base64.b64encode(encrypted).decode()
    
    def generate_random_name(self, length=8) -> str:
        """Генерирует случайное имя"""
        return ''.join(random.choices(string.ascii_letters, k=length))
    
    def get_obfuscated_strings(self) -> dict:
        """Возвращает обфусцированные строки для защиты"""
        critical_strings = [
            "generic",
            "google_sdk",
            "Emulator",
            "emulator",
            "Android SDK",
            "test-keys",
            "goldfish",
            "ranchu",
            "/system/app/Superuser.apk",
            "/sbin/su",
            "/system/bin/su",
            "/system/xbin/su",
            "su",
            "payload.bin",
            "frida",
            "gum-js-loop",
            "xposed",
            "magisk",
            "/dev/socket/qemud",
            "/dev/qemu_pipe"
        ]
        
        obfuscated = {}
        for s in critical_strings:
            obfuscated[s] = self.obfuscate_string(s)
        
        return obfuscated
    
    def generate_string_decoder(self) -> str:
        """Генерирует метод для расшифровки строк"""
        method_name = self.generate_random_name(6)
        return f'''
    private static String {method_name}(String s) {{
        try {{
            byte[] data = android.util.Base64.decode(s, android.util.Base64.DEFAULT);
            byte[] result = new byte[data.length];
            for (int i = 0; i < data.length; i++) {{
                result[i] = (byte)(data[i] ^ {self.string_key});
            }}
            return new String(result, "UTF-8");
        }} catch (Exception e) {{
            return "";
        }}
    }}''', method_name
    
    def generate_junk_methods(self, count=5) -> str:
        """Генерирует мусорные методы для запутывания"""
        methods = []
        for _ in range(count):
            var_name = self.generate_random_name(8)
            code = f'''
    private void {var_name}() {{
        int x = {random.randint(1000, 9999)};
        String s = "{self.generate_random_name(20)}";
        for (int i = 0; i < x; i++) {{
            x = (x * {random.randint(2, 9)}) % {random.randint(1000, 9999)};
            s = s.substring(0, Math.min(s.length(), {random.randint(5, 15)}));
        }}
    }}'''
            methods.append(code)
        return '\n'.join(methods)
    
    def generate_anti_tampering(self) -> str:
        """Генерирует код проверки целостности"""
        return '''
    private boolean checkIntegrity() {
        try {
            android.content.pm.PackageInfo packageInfo = 
                getPackageManager().getPackageInfo(getPackageName(), 
                android.content.pm.PackageManager.GET_SIGNATURES);
            
            for (android.content.pm.Signature signature : packageInfo.signatures) {
                byte[] signatureBytes = signature.toByteArray();
                java.security.MessageDigest md = java.security.MessageDigest.getInstance("SHA-256");
                byte[] digest = md.digest(signatureBytes);
                
                // Проверяем что подпись не изменена
                if (digest.length != 32) return false;
            }
            return true;
        } catch (Exception e) {
            return false;
        }
    }'''
