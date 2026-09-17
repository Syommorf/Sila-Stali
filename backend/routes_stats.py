from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import get_db
from models import Work, User
from auth import require_manager, require_worker

router = APIRouter(prefix="/stats", tags=["stats"])

WORKER_ROLES = ["apprentice", "bender", "senior_bender"]


class WorkerStat(BaseModel):
    worker_id: int
    worker_name: str
    total_quantity: int
    total_works: int
    avg_duration_minutes: Optional[float]
    parts_breakdown: dict


class OverviewStat(BaseModel):
    total_quantity: int
    total_works: int
    total_workers: int
    avg_duration_minutes: Optional[float]


class TimelinePeriod(BaseModel):
    period: str
    total_quantity: int
    total_works: int


@router.get("/overview")
def stats_overview(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    q = db.query(Work)
    if date_from:
        q = q.filter(Work.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Work.start_time <= datetime.combine(date_to, datetime.max.time()))

    total_quantity = q.with_entities(func.coalesce(func.sum(Work.quantity), 0)).scalar()
    total_works = q.count()
    total_workers = q.with_entities(func.count(func.distinct(Work.worker_id))).scalar()

    durations = []
    for w in q.all():
        if w.end_time and w.start_time:
            durations.append((w.end_time - w.start_time).total_seconds() / 60)
    avg_dur = round(sum(durations) / len(durations), 1) if durations else None

    return OverviewStat(
        total_quantity=total_quantity,
        total_works=total_works,
        total_workers=total_workers,
        avg_duration_minutes=avg_dur,
    )


@router.get("/by-worker", response_model=List[WorkerStat])
def stats_by_worker(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    q = db.query(Work).join(User, Work.worker_id == User.id)
    if date_from:
        q = q.filter(Work.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Work.start_time <= datetime.combine(date_to, datetime.max.time()))

    workers = db.query(User).filter(User.role.in_(WORKER_ROLES)).all()
    result = []
    for worker in workers:
        wq = q.filter(Work.worker_id == worker.id)
        works = wq.all()
        if not works:
            continue

        total_qty = sum(w.quantity for w in works)
        durations = []
        parts = {}
        for w in works:
            parts[w.part_number] = parts.get(w.part_number, 0) + w.quantity
            if w.end_time and w.start_time:
                durations.append((w.end_time - w.start_time).total_seconds() / 60)

        result.append(WorkerStat(
            worker_id=worker.id,
            worker_name=worker.full_name,
            total_quantity=total_qty,
            total_works=len(works),
            avg_duration_minutes=round(sum(durations) / len(durations), 1) if durations else None,
            parts_breakdown=parts,
        ))

    return sorted(result, key=lambda x: x.total_quantity, reverse=True)


@router.get("/my")
def my_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    group_by: str = "day",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_worker),
):
    if group_by not in ("day", "month", "year"):
        raise HTTPException(status_code=400, detail="group_by должен быть day|month|year")

    q = db.query(Work).filter(Work.worker_id == current_user.id)
    if date_from:
        q = q.filter(Work.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Work.start_time <= datetime.combine(date_to, datetime.max.time()))

    works = q.all()

    total_quantity = sum(w.quantity for w in works)
    durations = []
    for w in works:
        if w.end_time and w.start_time:
            durations.append((w.end_time - w.start_time).total_seconds() / 60)
    avg_dur = round(sum(durations) / len(durations), 1) if durations else None

    if group_by == "day":
        key = func.strftime("%Y-%m-%d", Work.start_time)
    elif group_by == "month":
        key = func.strftime("%Y-%m", Work.start_time)
    else:
        key = func.strftime("%Y", Work.start_time)

    rows = (
        q.with_entities(key, func.sum(Work.quantity), func.count(Work.id))
        .group_by(key)
        .order_by(key)
        .all()
    )
    periods = [
        TimelinePeriod(
            period=str(r[0]),
            total_quantity=int(r[1] or 0),
            total_works=int(r[2] or 0),
        )
        for r in rows
    ]

    return {
        "total_quantity": total_quantity,
        "total_works": len(works),
        "avg_duration_minutes": avg_dur,
        "periods": periods,
    }


@router.get("/timeline", response_model=List[TimelinePeriod])
def stats_timeline(
    group_by: str = "day",
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_manager),
):
    if group_by not in ("day", "month", "year"):
        raise HTTPException(status_code=400, detail="group_by должен быть day|month|year")

    q = db.query(Work)
    if date_from:
        q = q.filter(Work.start_time >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(Work.start_time <= datetime.combine(date_to, datetime.max.time()))

    if group_by == "day":
        key = func.strftime("%Y-%m-%d", Work.start_time)
    elif group_by == "month":
        key = func.strftime("%Y-%m", Work.start_time)
    else:
        key = func.strftime("%Y", Work.start_time)

    rows = (
        q.with_entities(key, func.sum(Work.quantity), func.count(Work.id))
        .group_by(key)
        .order_by(key)
        .all()
    )
    result = [
        TimelinePeriod(
            period=str(r[0]),
            total_quantity=int(r[1] or 0),
            total_works=int(r[2] or 0),
        )
        for r in rows
    ]
    return result