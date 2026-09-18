import os
from datetime import datetime, timezone, timedelta

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sila_stali.db")
SECRET_KEY = os.getenv("SECRET_KEY", "sila-stali-secret-key-change-in-production-2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8000

MOSCOW_TZ = timezone(timedelta(hours=3))

def moscow_now():
    return datetime.now(MOSCOW_TZ).replace(tzinfo=None)

# Обновление приложения
APK_VERSION = "1.3.0"           # версия в build.gradle (versionName)
APK_VERSION_CODE = 68          # версия в build.gradle (versionCode)
APK_DIR = "/opt/sila-stali-apk"
APK_FILENAME = "sila-stali-1.3.0.apk"
APK_FILE = os.path.join(APK_DIR, APK_FILENAME)
APK_URL = f"https://silastali.su/apk/{APK_FILENAME}"

# Обновление десктопного приложения (Windows)
DESKTOP_VERSION = "1.3.0"       # версия в app.py (VERSION)
DESKTOP_DIR = "/opt/sila-stali-desktop"
DESKTOP_FILENAME = "SilaStaliWindows.exe"
DESKTOP_FILE = os.path.join(DESKTOP_DIR, DESKTOP_FILENAME)
DESKTOP_URL = f"https://silastali.su/desktop/{DESKTOP_FILENAME}"

# Защита от копирования: SHA-256 отпечатки подписей APK
APK_CERT_HASHES = [
    "11a4c44cff0a7c1b013efa84e8c6200f622cfd0c5721c2b66132d851f58b6070",  # sideload (debug)
    "7d6da75d97c6e5157abcaa700ed389e49710cd6bfc7c55150648e66e044d9fd8",  # play release
]
