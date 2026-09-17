from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import get_db
from models import Work, User
from auth import get_current_user, require_manager

router = APIRouter(prefix="/works", tags=["works"])

WORKER_ROLES = ["apprentice", "bender", "senior_bender"]


class WorkCreate(BaseModel):
    part_number: str
    quantity: int
    note: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None


class WorkResponse(BaseModel):
    id: int
    worker_id: int
    worker_name: str
    part_number: str
    quantity: int
    note: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_minutes: Optional[float]

    class Config:
        from_attributes = True


class SyncRequest(BaseModel):
    works: List[WorkCreate]


@router.post("", status_code=201)
def create_work(work: WorkCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in WORKER_ROLES:
        raise HTTPException(status_code=403, detail="Работы создаёт гибщик")
    db_work = Work(
        worker_id=current_user.id,
        part_number=work.part_number,
        quantity=work.quantity,
        note=work.note,
        start_time=work.start_time,
        end_time=work.end_time,
    )
    db.add(db_work)
    db.commit()
    db.refresh(db_work)
    return {"id": db_work.id, "status": "created"}


@router.get("", response_model=List[WorkResponse])
def list_works(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    worker_id: Optional[int] = None,
    part_number: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Work).join(User, Work.worker_id == User.id)

    if current_user.role != "manager":
        q = q.filter(Work.worker_id == current_user.id)

    if date_from:
        q = q.filter(Work.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Work.start_time <= datetime.combine(date_to, datetime.max.time()))
    if worker_id:
        q = q.filter(Work.worker_id == worker_id)
    if part_number:
        q = q.filter(Work.part_number.ilike(f"%{part_number}%"))

    works = q.order_by(Work.start_time.desc()).all()

    result = []
    for w in works:
        duration = None
        if w.end_time and w.start_time:
            duration = (w.end_time - w.start_time).total_seconds() / 60
        result.append(WorkResponse(
            id=w.id,
            worker_id=w.worker_id,
            worker_name=w.worker.full_name,
            part_number=w.part_number,
            quantity=w.quantity,
            note=w.note or "",
            start_time=w.start_time,
            end_time=w.end_time,
            duration_minutes=round(duration, 1) if duration else None,
        ))
    return result


@router.post("/sync")
def sync_works(sync: SyncRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role not in WORKER_ROLES:
        raise HTTPException(status_code=403, detail="Работы создаёт гибщик")
    created = 0
    for w in sync.works:
        db_work = Work(
            worker_id=current_user.id,
            part_number=w.part_number,
            quantity=w.quantity,
            note=w.note,
            start_time=w.start_time,
            end_time=w.end_time,
            synced=1,
        )
        db.add(db_work)
        created += 1
    db.commit()
    return {"synced": created}


@router.get("/my")
def my_works(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    works = db.query(Work).filter(Work.worker_id == current_user.id).order_by(Work.start_time.desc()).limit(50).all()
    result = []
    for w in works:
        duration = None
        if w.end_time and w.start_time:
            duration = (w.end_time - w.start_time).total_seconds() / 60
        result.append({
            "id": w.id,
            "part_number": w.part_number,
            "quantity": w.quantity,
            "note": w.note or "",
            "start_time": w.start_time.isoformat(),
            "end_time": w.end_time.isoformat() if w.end_time else None,
            "duration_minutes": round(duration, 1) if duration else None,
        })
    return result


@router.delete("/{work_id}")
def delete_work(work_id: int, db: Session = Depends(get_db), current_user: User = Depends(require_manager)):
    db_work = db.query(Work).filter(Work.id == work_id).first()
    if not db_work:
        raise HTTPException(status_code=404, detail="Работа не найдена")
    worker = db.query(User).filter(User.id == db_work.worker_id).first()
    if worker is None or worker.role not in WORKER_ROLES:
        raise HTTPException(status_code=403, detail="Удалять можно только работы гибщиков")
    db.delete(db_work)
    db.commit()
    return {"status": "deleted"}
