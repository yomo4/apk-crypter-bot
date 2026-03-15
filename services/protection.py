"""
Модуль защитных механизмов для stub APK
"""


def generate_protection_code() -> str:
    """Генерирует Java код с защитными проверками"""
    return '''
    // Anti-debug проверка
    private boolean isDebuggerConnected() {
        return android.os.Debug.isDebuggerConnected();
    }
    
    // Anti-emulator проверка
    private boolean isEmulator() {
        String brand = android.os.Build.BRAND;
        String device = android.os.Build.DEVICE;
        String model = android.os.Build.MODEL;
        String product = android.os.Build.PRODUCT;
        String fingerprint = android.os.Build.FINGERPRINT;
        
        return brand.contains("generic") || device.contains("generic") ||
               model.contains("google_sdk") || model.contains("Emulator") ||
               model.contains("Android SDK") || product.contains("sdk") ||
               fingerprint.contains("generic") || fingerprint.contains("test-keys");
    }
    
    // Root detection
    private boolean isRooted() {
        String[] paths = {
            "/system/app/Superuser.apk",
            "/sbin/su", "/system/bin/su", "/system/xbin/su",
            "/data/local/xbin/su", "/data/local/bin/su",
            "/system/sd/xbin/su", "/system/bin/failsafe/su",
            "/data/local/su", "/su/bin/su"
        };
        
        for (String path : paths) {
            if (new java.io.File(path).exists()) return true;
        }
        
        try {
            Process p = Runtime.getRuntime().exec("su");
            p.destroy();
            return true;
        } catch (Exception e) {}
        
        return false;
    }
    
    // Проверка окружения
    private boolean checkEnvironment() {
        return !isDebuggerConnected() && !isEmulator() && !isRooted();
    }'''
