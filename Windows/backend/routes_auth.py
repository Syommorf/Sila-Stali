from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import User
from auth import verify_password, get_password_hash, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    full_name: str
    role: str
    block: Optional[str] = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    full_name: str


class EmployeeItem(BaseModel):
    id: int
    full_name: str
    username: str
    role: str


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    token = create_access_token(data={"sub": user.username})
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        full_name=user.full_name,
        role=user.role,
        block=user.block,
    )


@router.post("/login-chief", response_model=TokenResponse)
def login_chief(password: str = Form(...), db: Session = Depends(get_db)):
    """Вход руководителя по одному паролю (без логина)."""
    chiefs = (
        db.query(User)
        .filter(User.role.in_(["manager", "admin"]))
        .all()
    )
    for u in chiefs:
        if verify_password(password, u.password_hash):
            token = create_access_token(data={"sub": u.username})
            return TokenResponse(
                access_token=token,
                token_type="bearer",
                user_id=u.id,
                full_name=u.full_name,
                role=u.role,
                block=u.block,
            )
    raise HTTPException(status_code=401, detail="Неверный пароль")


@router.get("/employees", response_model=List[EmployeeItem])
def list_employees(block: Optional[str] = None, db: Session = Depends(get_db)):
    """Публичный список рабочих (для входа сотрудника без логина)."""
    query = db.query(User).filter(
        User.role.in_(["apprentice", "bender", "senior_bender",
                       "laser_cutter", "fitter", "welder", "storekeeper"])
    )
    if block:
        query = query.filter(User.block == block)
    workers = query.order_by(User.full_name).all()
    return [
        EmployeeItem(id=u.id, full_name=u.full_name, username=u.username, role=u.role)
        for u in workers
    ]


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "block": current_user.block,
    }
