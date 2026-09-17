from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models import User, Chat, ChatMember, ChatMessage, ChatRead
from auth import get_current_user
from config import moscow_now

router = APIRouter(prefix="/chat", tags=["chat"])

BLOCK_LASER = "laser"
BLOCK_BENDER = "bender"
BLOCK_FITTER = "fitter"
BLOCK_WELDER = "welder"
BLOCK_STOREKEEPER = "storekeeper"
BLOCK_CHIEF = "chief"
BLOCK_KEYS = [BLOCK_LASER, BLOCK_BENDER, BLOCK_FITTER, BLOCK_WELDER, BLOCK_STOREKEEPER]
WORKER_ROLES = ["apprentice", "bender", "senior_bender",
                "laser_cutter", "fitter", "welder", "storekeeper"]
MANAGING = ("manager", "admin")

# Каналы: (ключ, название, block-значение; None = общий)
CHANNELS = [
    ("general", "Общий", None),
    (BLOCK_LASER, "Лазер", BLOCK_LASER),
    (BLOCK_BENDER, "Гибка", BLOCK_BENDER),
    (BLOCK_FITTER, "Слесарка", BLOCK_FITTER),
    (BLOCK_WELDER, "Сварка", BLOCK_WELDER),
    (BLOCK_STOREKEEPER, "Склад", BLOCK_STOREKEEPER),
    (BLOCK_CHIEF, "Руководство", BLOCK_CHIEF),
]


def ensure_channels(db: Session):
    """Создаёт все каналы, если их ещё нет (идемпотентно)."""
    for key, name, block in CHANNELS:
        chat = db.query(Chat).filter(
            Chat.type == "channel", Chat.block.is_(None) if block is None else Chat.block == block
        ).first()
        if not chat:
            db.add(Chat(type="channel", name=name, block=block))
    db.commit()


def sync_user_channels(db: Session, user: User):
    """Приводит членства пользователя в каналах в соответствие с ролью и блоком."""
    ensure_channels(db)
    eligible = {None}  # «Общий» — все
    if user.role in MANAGING:
        eligible |= set(BLOCK_KEYS + [BLOCK_CHIEF])
    elif user.block in BLOCK_KEYS:
        eligible.add(user.block)
    channels = db.query(Chat).filter(Chat.type == "channel").all()
    for chat in channels:
        if chat.block in eligible or (chat.block is None and None in eligible):
            if not db.query(ChatMember).filter(
                    ChatMember.chat_id == chat.id, ChatMember.user_id == user.id).first():
                db.add(ChatMember(chat_id=chat.id, user_id=user.id, role="member"))
    # удаляем из каналов, куда больше не положено
    for member in db.query(ChatMember).filter(ChatMember.user_id == user.id).all():
        chat = db.query(Chat).filter(Chat.id == member.chat_id, Chat.type == "channel").first()
        if chat:
            if chat.block not in eligible and not (chat.block is None and None in eligible):
                db.query(ChatRead).filter(
                    ChatRead.chat_id == chat.id, ChatRead.user_id == user.id).delete()
                db.delete(member)
    db.commit()


def purge_user_chat_data(db: Session, user_id: int):
    """Удаляет чат-данные пользователя (при удалении аккаунта)."""
    members = db.query(ChatMember).filter(ChatMember.user_id == user_id).all()
    for member in members:
        chat = member.chat
        if chat is None:
            continue
        others = db.query(ChatMember).filter(
            ChatMember.chat_id == chat.id, ChatMember.user_id != user_id).count()
        if chat.type == "dm" and others <= 1:
            db.query(ChatRead).filter(ChatRead.chat_id == chat.id).delete()
            db.delete(chat)  # каскадом удалит участников и сообщения
        else:
            db.query(ChatRead).filter(
                ChatRead.chat_id == chat.id, ChatRead.user_id == user_id).delete()
            db.delete(member)
    db.query(ChatRead).filter(ChatRead.user_id == user_id).delete()
    db.commit()


def _iso(dt):
    return dt.isoformat() if dt else None


def _msg_dict(m: ChatMessage) -> dict:
    sender = m.sender
    return {
        "id": m.id,
        "chat_id": m.chat_id,
        "sender_id": m.sender_id,
        "sender_name": sender.full_name if sender else None,
        "sender_block": sender.block if sender else None,
        "text": m.text,
        "created_at": _iso(m.created_at),
        "edited_at": _iso(m.edited_at),
        "deleted": bool(m.deleted),
    }


def _chat_dict(db: Session, chat: Chat, user: User) -> dict:
    last_msg = (
        db.query(ChatMessage)
        .filter(ChatMessage.chat_id == chat.id, ChatMessage.deleted == 0)
        .order_by(ChatMessage.id.desc())
        .first()
    )
    read = db.query(ChatRead).filter(
        ChatRead.chat_id == chat.id, ChatRead.user_id == user.id).first()
    last_read = read.last_message_id if read else 0
    unread = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat.id,
        ChatMessage.deleted == 0,
        ChatMessage.id > last_read,
    ).count()
    members = db.query(ChatMember).filter(ChatMember.chat_id == chat.id).count()
    other_user_id = None
    other_user_name = None
    if chat.type == "dm":
        om = db.query(ChatMember).filter(
            ChatMember.chat_id == chat.id, ChatMember.user_id != user.id).first()
        if om:
            other_user_id = om.user_id
            other_user_name = om.user.full_name if om.user else None
    return {
        "id": chat.id,
        "type": chat.type,
        "name": chat.name,
        "block": chat.block,
        "created_at": _iso(chat.created_at),
        "member_count": members,
        "unread_count": unread,
        "last_message": _msg_dict(last_msg) if last_msg else None,
        "other_user_id": other_user_id,
        "other_user_name": other_user_name,
    }


def _require_member(db: Session, chat_id: int, user: User) -> Chat:
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if not db.query(ChatMember).filter(
            ChatMember.chat_id == chat.id, ChatMember.user_id == user.id).first():
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    return chat


class SendMessageRequest(BaseModel):
    text: str


class DmRequest(BaseModel):
    user_id: int


class CreateChatRequest(BaseModel):
    name: str
    member_ids: List[int] = []


class ReadRequest(BaseModel):
    last_message_id: int


class AddMembersRequest(BaseModel):
    user_ids: List[int] = []


def _mark_read(db: Session, chat_id: int, user_id: int, last_message_id: int):
    row = db.query(ChatRead).filter(
        ChatRead.chat_id == chat_id, ChatRead.user_id == user_id).first()
    if row:
        if last_message_id > row.last_message_id:
            row.last_message_id = last_message_id
    else:
        db.add(ChatRead(chat_id=chat_id, user_id=user_id, last_message_id=last_message_id))
    db.commit()


@router.get("/list")
def chat_list(db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    members = db.query(ChatMember).filter(
        ChatMember.user_id == current_user.id).all()
    chats = [m.chat for m in members if m.chat is not None]

    def sort_key(chat: Chat):
        last = db.query(ChatMessage).filter(
            ChatMessage.chat_id == chat.id, ChatMessage.deleted == 0
        ).order_by(ChatMessage.id.desc()).first()
        return last.id if last else 0

    chats.sort(key=sort_key, reverse=True)
    return [_chat_dict(db, c, current_user) for c in chats]


@router.get("/{chat_id}/messages")
def chat_messages(chat_id: int, after_id: int = 0, limit: int = 200,
                  db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    chat = _require_member(db, chat_id, current_user)
    limit = max(1, min(limit, 500))
    q = db.query(ChatMessage).filter(
        ChatMessage.chat_id == chat.id, ChatMessage.deleted == 0)
    if after_id > 0:
        q = q.filter(ChatMessage.id > after_id)
        q = q.order_by(ChatMessage.id.asc())
        messages = q.limit(limit).all()
    else:
        messages = q.order_by(ChatMessage.id.desc()).limit(limit).all()
        messages.reverse()
    return {"chat_id": chat.id, "messages": [_msg_dict(m) for m in messages]}


@router.post("/{chat_id}/messages")
def send_message(chat_id: int, body: SendMessageRequest,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    chat = _require_member(db, chat_id, current_user)
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Пустое сообщение")
    if len(text) > 4000:
        raise HTTPException(status_code=400, detail="Сообщение слишком длинное")
    msg = ChatMessage(chat_id=chat.id, sender_id=current_user.id, text=text)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    _mark_read(db, chat.id, current_user.id, msg.id)
    return _msg_dict(msg)


@router.post("/dm")
def open_dm(body: DmRequest, db: Session = Depends(get_db),
            current_user: User = Depends(get_current_user)):
    if body.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя написать самому себе")
    target = db.query(User).filter(User.id == body.user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    existing = None
    for m in db.query(ChatMember).filter(ChatMember.user_id == current_user.id).all():
        if m.chat and m.chat.type == "dm":
            in_target = db.query(ChatMember).filter(
                ChatMember.chat_id == m.chat.id, ChatMember.user_id == body.user_id).first()
            if in_target:
                existing = m.chat
                break
    if existing:
        return _chat_dict(db, existing, current_user)
    chat = Chat(type="dm", name=None)
    db.add(chat)
    db.flush()
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="member"))
    db.add(ChatMember(chat_id=chat.id, user_id=target.id, role="member"))
    db.commit()
    db.refresh(chat)
    return _chat_dict(db, chat, current_user)


@router.post("/create")
def create_chat(body: CreateChatRequest, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Название не может быть пустым")
    if len(name) > 100:
        raise HTTPException(status_code=400, detail="Название слишком длинное")
    chat = Chat(type="group", name=name, created_by=current_user.id)
    db.add(chat)
    db.flush()
    ids = set(body.member_ids)
    ids.discard(current_user.id)
    db.add(ChatMember(chat_id=chat.id, user_id=current_user.id, role="creator"))
    for uid in ids:
        if db.query(User).filter(User.id == uid).first():
            db.add(ChatMember(chat_id=chat.id, user_id=uid, role="member"))
    db.commit()
    db.refresh(chat)
    return _chat_dict(db, chat, current_user)


@router.post("/{chat_id}/read")
def mark_read(chat_id: int, body: ReadRequest,
              db: Session = Depends(get_db),
              current_user: User = Depends(get_current_user)):
    _require_member(db, chat_id, current_user)
    _mark_read(db, chat_id, current_user.id, body.last_message_id)
    return {"status": "ok"}


@router.post("/{chat_id}/members")
def add_members(chat_id: int, body: AddMembersRequest,
                db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat.id, ChatMember.user_id == current_user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="Нет доступа к чату")
    if chat.type == "channel":
        raise HTTPException(status_code=400, detail="Каналом управляет система")
    if member.role != "creator" and current_user.role not in MANAGING:
        raise HTTPException(status_code=403, detail="Только создатель чата может добавлять участников")
    for uid in body.user_ids:
        if uid == current_user.id:
            continue
        if not db.query(User).filter(User.id == uid).first():
            continue
        if not db.query(ChatMember).filter(
                ChatMember.chat_id == chat.id, ChatMember.user_id == uid).first():
            db.add(ChatMember(chat_id=chat.id, user_id=uid, role="member"))
    db.commit()
    return {"status": "ok"}


@router.delete("/{chat_id}/members/me")
def leave_chat(chat_id: int, db: Session = Depends(get_db),
               current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat.id, ChatMember.user_id == current_user.id).first()
    if member:
        db.query(ChatRead).filter(
            ChatRead.chat_id == chat.id, ChatRead.user_id == current_user.id).delete()
        db.delete(member)
        db.commit()
    return {"status": "ok"}


@router.delete("/{chat_id}")
def delete_chat(chat_id: int, db: Session = Depends(get_db),
                current_user: User = Depends(get_current_user)):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=404, detail="Чат не найден")
    if chat.type == "channel":
        raise HTTPException(status_code=400, detail="Канал нельзя удалить")
    member = db.query(ChatMember).filter(
        ChatMember.chat_id == chat.id, ChatMember.user_id == current_user.id).first()
    is_creator = member is not None and member.role == "creator"
    if not is_creator and current_user.role not in MANAGING:
        raise HTTPException(status_code=403, detail="Только создатель чата может его удалить")
    db.query(ChatRead).filter(ChatRead.chat_id == chat.id).delete()
    db.delete(chat)
    db.commit()
    return {"status": "deleted"}