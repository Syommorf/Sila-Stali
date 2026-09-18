from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from config import moscow_now
from database import get_db
from models import (
    User,
    OrderItemClaim,
    OrderItemClaimWorker,
)
from auth import get_current_user

router = APIRouter(prefix="/crew-invites", tags=["crew-invites"])

WORKER_ROLES = ["apprentice", "bender", "senior_bender"]

_name_cache: dict = {}


def _name(db: Session, uid: int) -> str:
    if uid in _name_cache:
        return _name_cache[uid]
    u = db.query(User).filter(User.id == uid).first()
    name = (u.full_name if u else "") or (u.username if u else "") or "?"
    _name_cache[uid] = name
    return name


class InviteItem(BaseModel):
    id: int
    claim_id: int
    item_id: int
    part_number: str
    order_id: int
    order_number: str
    quantity: int
    inviter_name: str
    worker_id: int
    invited_at: str


@router.get("")
def my_invites(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Мои приглашения в бригаду, ожидающие ответа."""
    if current_user.role not in WORKER_ROLES:
        return []
    rows = (
        db.query(OrderItemClaimWorker)
        .filter(
            OrderItemClaimWorker.worker_id == current_user.id,
            OrderItemClaimWorker.status == "pending",
            OrderItemClaim.completed_at.is_(None),
        )
        .join(OrderItemClaim)
        .add_columns(OrderItemClaim)
        .order_by(OrderItemClaimWorker.invited_at.desc())
        .all()
    )
    result = []
    for part, claim in rows:
        if claim is None or claim.item is None:
            continue
        order = claim.item.order
        result.append(InviteItem(
            id=part.id,
            claim_id=claim.id,
            item_id=claim.item.id,
            part_number=claim.item.part_number,
            order_id=order.id if order else 0,
            order_number=order.order_number if order else "",
            quantity=claim.item.quantity,
            inviter_name=_name(db, part.invited_by) if part.invited_by else _name(db, claim.worker_id),
            worker_id=claim.worker_id,
            invited_at=part.invited_at.isoformat() if part.invited_at else "",
        ).dict())
    return result


class RespondRequest(BaseModel):
    accept: bool


@router.post("/{invite_id}/respond")
def respond_invite(
    invite_id: int,
    body: RespondRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Соисполнитель принимает или отклоняет приглашение в бригаду."""
    part = db.query(OrderItemClaimWorker).filter(OrderItemClaimWorker.id == invite_id).first()
    if not part or part.worker_id != current_user.id:
        raise HTTPException(status_code=404, detail="Приглашение не найдено")
    if part.status != "pending":
        raise HTTPException(status_code=400, detail="Уже обработано")

    part.status = "accepted" if body.accept else "declined"
    part.responded_at = moscow_now()
    db.commit()
    return {"id": part.id, "status": part.status, "accepted": body.accept}
