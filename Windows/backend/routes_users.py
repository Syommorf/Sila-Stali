from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import User, Work
from auth import get_current_user, get_password_hash, verify_password
from routes_chat import sync_user_channels, purge_user_chat_data

router = APIRouter(prefix="/users", tags=["users"])

WORKER_ROLES = ["apprentice", "bender", "senior_bender", "laser_cutter", "fitter", "welder", "storekeeper"]
MANAGER_ROLE = "manager"
ADMIN_ROLE = "admin"
BLOCK_LASER = "laser"
BLOCK_BENDER = "bender"
BLOCK_FITTER = "fitter"
BLOCK_WELDER = "welder"
BLOCK_STOREKEEPER = "storekeeper"
BLOCK_CHIEF = "chief"
WORKER_BLOCKS = [BLOCK_LASER, BLOCK_BENDER, BLOCK_FITTER, BLOCK_WELDER, BLOCK_STOREKEEPER]
BLOCKS = WORKER_BLOCKS + [BLOCK_CHIEF]


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "bender"
    block: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    password: Optional[str] = None
    username: Optional[str] = None
    block: Optional[str] = None


class UserMeUpdate(BaseModel):
    current_password: str
    new_username: Optional[str] = None
    new_password: Optional[str] = None


def _forbidden(detail: str):
    raise HTTPException(status_code=403, detail=detail)


def _check_username_unique(db: Session, username: str, exclude_id: Optional[int] = None):
    q = db.query(User).filter(User.username == username)
    if exclude_id:
        q = q.filter(User.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=400, detail="Такой логин уже занят")


def _user_dict(user: User, include_password: bool = False) -> dict:
    d = {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "block": user.block,
    }
    if include_password:
        d["password_plain"] = user.password_plain
    return d


def _default_block(role: str) -> str:
    return BLOCK_CHIEF if role == MANAGER_ROLE else BLOCK_BENDER


def _check_block_for_role(role: str, block: Optional[str]):
    if block is None:
        return
    if block not in BLOCKS:
        raise HTTPException(status_code=400, detail="Недопустимый блок")
    if role in WORKER_ROLES and block == BLOCK_CHIEF:
        raise HTTPException(status_code=400,
                            detail="Рабочему нельзя назначить блок «Руководство»")


@router.get("")
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == ADMIN_ROLE:
        users = db.query(User).filter(User.role != ADMIN_ROLE).order_by(User.full_name).all()
        return [_user_dict(u, include_password=True) for u in users]
    if current_user.role == MANAGER_ROLE or current_user.role in WORKER_ROLES:
        # список всех сотрудников (начальник, старший гибщик, гибщик, ученик — и будущие роли)
        users = db.query(User).filter(User.role != ADMIN_ROLE).order_by(User.full_name).all()
        is_manager = current_user.role == MANAGER_ROLE
        # начальник видит пароли только своих подчинённых (гибщиков)
        return [_user_dict(u, include_password=(is_manager and u.role in WORKER_ROLES)) for u in users]
    _forbidden("Доступ запрещён")


@router.post("", status_code=201)
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _check_username_unique(db, user.username)

    if user.role == ADMIN_ROLE:
        raise HTTPException(status_code=400, detail="Нельзя создать администратора")

    if current_user.role == ADMIN_ROLE:
        if user.role != MANAGER_ROLE and user.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Недопустимая роль")
    elif current_user.role == MANAGER_ROLE:
        if user.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Начальник может создавать только сотрудников")
    else:
        _forbidden("Доступ запрещён")

    block = user.block or (BLOCK_CHIEF if user.role == MANAGER_ROLE else BLOCK_BENDER)
    _check_block_for_role(user.role, block)
    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        password_plain=user.password,
        full_name=user.full_name,
        role=user.role,
        block=block,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    sync_user_channels(db, db_user)
    return {"id": db_user.id, "status": "created"}


@router.put("/me")
def update_me(data: UserMeUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль неверен")

    new_username = data.new_username
    new_password = data.new_password

    if current_user.role == ADMIN_ROLE:
        raise HTTPException(status_code=400, detail="Администратору нельзя менять свои данные в этом разделе")

    if new_username and new_username != current_user.username:
        _check_username_unique(db, new_username, exclude_id=current_user.id)
        current_user.username = new_username
    if new_password:
        current_user.password_hash = get_password_hash(new_password)
        current_user.password_plain = new_password

    db.commit()
    return {"status": "updated", "username": current_user.username}


@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if db_user.role == ADMIN_ROLE:
        _forbidden("Нельзя изменять администратора")

    if current_user.role == ADMIN_ROLE:
        if data.role and data.role != MANAGER_ROLE and data.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Недопустимая роль")
    elif current_user.role == MANAGER_ROLE:
        if db_user.role not in WORKER_ROLES:
            _forbidden("Начальник управляет только сотрудниками")
        if data.role and data.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Недопустимая должность")
    else:
        _forbidden("Доступ запрещён")

    if data.full_name:
        db_user.full_name = data.full_name
    if data.role:
        db_user.role = data.role
    if db_user.role in WORKER_ROLES and db_user.block == BLOCK_CHIEF:
        db_user.block = BLOCK_BENDER
    if data.block is not None and data.block != db_user.block:
        if data.block not in BLOCKS:
            raise HTTPException(status_code=400, detail="Недопустимый блок")
        if db_user.role in WORKER_ROLES and data.block == BLOCK_CHIEF:
            raise HTTPException(status_code=400,
                                detail="Рабочему нельзя назначить блок «Руководство»")
        db_user.block = data.block
    if data.password:
        db_user.password_hash = get_password_hash(data.password)
        db_user.password_plain = data.password
    if data.username:
        if data.username != db_user.username:
            _check_username_unique(db, data.username, exclude_id=db_user.id)
            db_user.username = data.username
    db.commit()
    sync_user_channels(db, db_user)
    return {"status": "updated"}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if db_user.role == ADMIN_ROLE:
        _forbidden("Нельзя удалить администратора")
    if db_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить себя")

    if current_user.role == ADMIN_ROLE:
        pass
    elif current_user.role == MANAGER_ROLE:
        if db_user.role not in WORKER_ROLES:
            _forbidden("Начальник удаляет только сотрудников")
    else:
        _forbidden("Доступ запрещён")

    purge_user_chat_data(db, db_user.id)
    db.query(Work).filter(Work.worker_id == db_user.id).delete()
    db.delete(db_user)
    db.commit()
    return {"status": "deleted"}