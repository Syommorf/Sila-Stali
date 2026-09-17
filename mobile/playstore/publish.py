#!/usr/bin/env python3
"""Загрузка «Сила стали» в Google Play через Play Developer API.

Требует:
  1) Аккаунт разработчика Google Play (оплаченные $25), соглашение DDA принято.
  2) Сервисный ключ (JSON):
       Play Console -> Setup/Настройка -> API access -> Create service account
       -> в Google Cloud создать ключ (JSON) -> вернуться, службе дать роль
       "Release manager" (или права перевода в треки и редактирования приложения).
     Файл ключа ложить рядом: playstore/play-service-account.json (или --key).

Примеры:
  python publish.py --key play-service-account.json            (создать приложение, если нет)
  python publish.py --key play-service-account.json --skip-create
"""

import argparse
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

PKG = "com.silastali.app"
TITLE = "Сила стали"
SHORT = "Учёт работы цеха: работы, детали, смены и статистика для сотрудников ООО «Сила стали»."
FULL = (
    "Сила стали — мобильное приложение для учёта работы цеха металлообработки. "
    "Ведите журнал выполненных работ, вводите количество деталей со сканера штрих-кодов, "
    "следите за нормами и статистикой в реальном времени.\n\n"
    "Возможности:\n"
    "• Приём работ и ввод выполненных деталей со сканером штрих-кодов\n"
    "• Личная статистика гибщика: детали, вес и норма за смену\n"
    "• Общие списки работ и статистика по цеху для мастера\n"
    "• Управление сотрудниками и расчёт показателей для администратора\n"
    "• Вход по логину и паролю или по личному ПИН-коду\n"
    "• Экспорт данных для бухгалтерии\n\n"
    "Приложение предназначено для сотрудников и администрации компании."
)
HERE = os.path.dirname(os.path.abspath(__file__))
AAB = os.path.join(HERE, "app-play-release.aab")
FEATURE = os.path.join(HERE, "feature-graphic-1024x500.png")
SCOPE = ["https://www.googleapis.com/auth/androidpublisher"]


def creds_from(key_path):
    creds = service_account.Credentials.from_service_account_file(key_path, scopes=SCOPE)
    creds.refresh(Request())
    return creds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", default=os.path.join(HERE, "play-service-account.json"))
    ap.add_argument("--aab", default=AAB)
    ap.add_argument("--pkg", default=PKG)
    ap.add_argument("--create", action="store_true", default=True,
                    help="создать приложение через API при отсутствии")
    ap.add_argument("--skip-create", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.key):
        print("НЕТ КЛЮЧА:", args.key)
        print("Сделайте сервисный ключ в Play Console (см. шапку скрипта) и положите его " +
              "в playstore/play-service-account.json")
        sys.exit(2)
    if not os.path.exists(args.aab):
        print("НЕТ AAB:", args.aab)
        sys.exit(2)

    creds = creds_from(args.key)
    service = build("androidpublisher", "v3", credentials=creds,
                    static_discovery=False, cache_discovery=False)

    pkg = args.pkg

    if not args.skip_create:
        try:
            create_body = {
                "packageName": pkg,
                "title": TITLE,
                "languages": ["ru-RU"],
            }
            app = service.apps().create(body=create_body).execute()
            print("[OK] Приложение создано:", app.get("title"), "-", app.get("packageName"))
        except HttpError as e:
            details = e.content.decode(errors="replace")
            if "already" in details.lower() or e.resp.status == 409:
                print("[i] Приложение уже существует на аккаунте:", pkg)
            elif e.resp.status in (403, 401):
                print("[!]", details)
                print("  Проверьте: аккаунт оплачен, DDA принято, у сервисного ключа есть роль.")
                sys.exit(3)
            else:
                print("[i] Создание через API не удалось:", details)
                print("[i] Создайте приложение вручную в Play Console (All apps -> Create app,\n"
                      "    package =", pkg, ", title =", TITLE, ") и перезапустите с --skip-create")

    list_out = None
    try:
        list_out = service.applications().get(packageName=pkg).execute()
    except HttpError:
        pass
    if list_out is None:
        print("[!] Приложение", pkg, "не найдено на аккаунте.")
        sys.exit(3)

    edit = service.edits().insert(packageName=pkg, body={}).execute()
    eid = edit["id"]
    print("[OK] Edit создан:", eid)

    print("[..] Загружаю AAB:", args.aab)
    mb = MediaFileUpload(args.aab, mimetype="application/octet-stream", resumable=True)
    bundle = None
    while True:
        status, bundle = service.edits().bundles().upload(
            packageName=pkg, editId=eid, media_body=mb, body={}
        ).next_chunk()
        if status is None:
            break
    print("[OK] AAB загружен. versionCode:", bundle["versionCode"])

    listing = {
        "language": "ru-RU",
        "title": TITLE,
        "shortDescription": SHORT,
        "fullDescription": FULL,
    }
    try:
        service.edits().listings().update(
            packageName=pkg, editId=eid, language="ru-RU", body=listing
        ).execute()
        print("[OK] Заполнено описание (ru-RU)")
    except HttpError as e:
        print("[!] Описание не записалось:", e.content.decode(errors="replace"))

    if os.path.exists(FEATURE):
        try:
            service.edits().images().upload(
                packageName=pkg, editId=eid, language="ru-RU",
                imageType="featureGraphic",
                media_body=MediaFileUpload(FEATURE, mimetype="image/png"),
            ).execute()
            print("[OK] Загружена feature graphic")
        except HttpError as e:
            print("[!] Feature graphic:", e.content.decode(errors="replace"))

    track_body = {
        "releases": [{
            "name": "3.2",
            "status": "completed",
            "versionCodes": [int(bundle["versionCode"])],
            "releaseNotes": [{
                "language": "ru-RU",
                "text": "Первая публикация: ведение учёта работ в цехе.",
            }],
        }]
    }
    track_ok = True
    try:
        service.edits().tracks().update(
            packageName=pkg, editId=eid, track="internal", body=track_body
        ).execute()
        print("[OK] Релиз добавлен в трек internal (внутреннее тестирование)")
    except HttpError as e:
        track_ok = False
        print("[!] Трек internal:", e.content.decode(errors="replace"))

    try:
        service.edits().commit(packageName=pkg, editId=eid).execute()
        print("[OK] Изменения сохранены (edit commit)")
    except HttpError as e:
        print("[X] commit:", e.content.decode(errors="replace"))
        sys.exit(4)

    print()
    print("======= ЧТО ДАЛЬШЕ =======")
    if not track_ok:
        print("- Откройте Play Console ->", pkg, "-> Internal testing -> переведите AAB в релиз")
    print("- В Play Console заполните: значок магазина (icon-512.png), скриншоты, категорию,")
    print("  опросники (аудитория/контент), Data safety, политику конфиденциальности.")
    print("- Выложите политику конфиденциальности в интернет и укажите её URL.")
    print("- Затем: тестирование -> Review -> Production.")


if __name__ == "__main__":
    main()