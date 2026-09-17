from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from database import engine, Base, SessionLocal
from models import User, Work
from auth import get_password_hash
from config import APK_VERSION, APK_VERSION_CODE, APK_FILE, APK_DIR, APK_URL
from middleware_cert import CertMiddleware
import os
from routes_auth import router as auth_router
from routes_works import router as works_router
from routes_stats import router as stats_router
from routes_users import router as users_router
from routes_export import router as export_router
from routes_orders import router as orders_router
from routes_orders import purge_expired_archive
from routes_invites import router as invites_router
from routes_chat import router as chat_router
from routes_chat import ensure_channels, sync_user_channels

app = FastAPI(title="Сила стали API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CertMiddleware)

app.include_router(auth_router)
app.include_router(works_router)
app.include_router(stats_router)
app.include_router(users_router)
app.include_router(export_router)
app.include_router(orders_router)
app.include_router(invites_router)
app.include_router(chat_router)


@app.get("/app/update")
def app_update():
    exists = os.path.exists(APK_FILE)
    size = os.path.getsize(APK_FILE) if exists else 0
    return {
        "available": exists,
        "version": APK_VERSION,
        "version_code": APK_VERSION_CODE,
        "apk_size": size,
        "apk_url": APK_URL if exists else None,
    }


app.mount("/apk", StaticFiles(directory=APK_DIR, check_dir=False), name="apk")


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Миграция: колонка password_plain (идемпотентно; при 2 воркерах бывает гонка — не падаем)
        try:
            table_cols = [r[1] for r in db.execute(text("PRAGMA table_info(users)")).fetchall()]
            if "password_plain" not in table_cols:
                db.execute(text("ALTER TABLE users ADD COLUMN password_plain VARCHAR(100)"))
                db.commit()
        except Exception:
            db.rollback()
        try:
            db.execute(text("UPDATE users SET password_plain = '2872' WHERE username = 'More' AND password_plain IS NULL"))
            db.commit()
        except Exception:
            db.rollback()

        # Миграция: колонка block (блок/участок) в users
        try:
            ublock_cols = [r[1] for r in db.execute(text("PRAGMA table_info(users)")).fetchall()]
            if "block" not in ublock_cols:
                db.execute(text("ALTER TABLE users ADD COLUMN block VARCHAR(30)"))
                db.commit()
        except Exception:
            db.rollback()
        try:
            db.execute(text("UPDATE users SET block = 'chief' WHERE username = 'More' AND block IS NULL"))
            db.commit()
        except Exception:
            db.rollback()

        # Миграция: колонка ready_at в spec_orders (архив «готов»)
        try:
            order_cols = [r[1] for r in db.execute(text("PRAGMA table_info(spec_orders)")).fetchall()]
            if "ready_at" not in order_cols:
                db.execute(text("ALTER TABLE spec_orders ADD COLUMN ready_at DATETIME"))
                db.commit()
        except Exception:
            db.rollback()
        # Миграция: стадия выполнения в order_item_completions (блоки заказов)
        try:
            comp_cols = [r[1] for r in db.execute(text("PRAGMA table_info(order_item_completions)")).fetchall()]
            if "stage" not in comp_cols:
                db.execute(text("ALTER TABLE order_item_completions ADD COLUMN stage VARCHAR(20) DEFAULT 'bender'"))
                db.commit()
        except Exception:
            db.rollback()

        purge_expired_archive(db, commit=True)

        # Миграция: статусы приглашений в бригаду (идемпотентно)
        try:
            cw_cols = [r[1] for r in db.execute(text("PRAGMA table_info(order_item_claim_workers)")).fetchall()]
            if "status" not in cw_cols:
                db.execute(text("ALTER TABLE order_item_claim_workers ADD COLUMN status VARCHAR(20) DEFAULT 'accepted' NOT NULL"))
                db.execute(text("ALTER TABLE order_item_claim_workers ADD COLUMN invited_by INTEGER"))
                db.execute(text("ALTER TABLE order_item_claim_workers ADD COLUMN invited_at DATETIME"))
                db.execute(text("ALTER TABLE order_item_claim_workers ADD COLUMN responded_at DATETIME"))
                db.commit()
        except Exception:
            db.rollback()

        # Миграция со старой схемы (однократно, только для старых баз): если существует
        # старый пользователь "admin" и ещё нет нового админа "More" — очищаем старую схему.
        # ВАЖНО: при наличии "More" персонал (в т.ч. менеджер с логином "admin") НЕ удаляется.
        old_admin = db.query(User).filter(User.username == "admin").first()
        more_user = db.query(User).filter(User.username == "More").first()
        if old_admin and not more_user:
            db.query(Work).delete()
            db.query(User).delete()
            db.commit()

        if not db.query(User).filter(User.username == "More").first():
            admin = User(
                username="More",
                password_hash=get_password_hash("2872"),
                password_plain="2872",
                full_name="Администратор",
                role="admin",
                block="chief",
            )
            db.add(admin)
            db.commit()

        # Чат: создаём каналы и привязываем всех пользователей по их ролям/блокам
        ensure_channels(db)
        for user in db.query(User).all():
            sync_user_channels(db, user)
    except IntegrityError:
        db.rollback()
    finally:
        db.close()


@app.get("/")
def root():
    return {"app": "Сила стали", "version": "1.0.0"}


@app.get("/health")
def health():
    return {"status": "ok"}
