import traceback
import re
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
from config import moscow_now
from database import get_db
from models import (
    User,
    SpecOrder,
    OrderItem,
    OrderItemCompletion,
    OrderItemClaim,
    OrderItemClaimWorker,
)
from auth import get_current_user

router = APIRouter(prefix="/orders", tags=["orders"])

WORKER_ROLES = ["apprentice", "bender", "senior_bender", "laser_cutter", "fitter", "welder", "storekeeper"]
MANAGING_ROLES = ["manager", "admin"]

# стадии маршрута -> блоки заказов
STAGE_NAMES = {
    "laser": "Лазер",
    "bender": "Гибка",
    "welder": "Сварка",
    "fitter": "Мех.обработка",
    "trubo": "Труборез",
}
PROD_STAGES = set(STAGE_NAMES.keys())
BLOCK_STOREKEEPER = "storekeeper"
_ROUTE_TOKEN_RE = re.compile(r"[+\s,;|\/\-]+")


def _route_stages(route):
    """Стадии детали из маршрута: Л->laser, Г->bender, Св->welder, М->fitter, Т->trubo."""
    if not route:
        return []
    stages = []
    seen = set()
    for tok in _ROUTE_TOKEN_RE.split(str(route).upper()):
        tok = tok.strip()
        if not tok:
            continue
        s = None
        if tok in ("Г", "ГИБ"):
            s = "bender"
        elif tok in ("Л", "ЛАЗ"):
            s = "laser"
        elif tok in ("СВ", "СВАР"):
            s = "welder"
        elif tok in ("М", "МЕХ"):
            s = "fitter"
        elif tok == "Т" or tok.startswith("ТРУБ"):
            s = "trubo"
        if s and s not in seen:
            seen.add(s)
            stages.append(s)
    return stages


def _has_untracked_tokens(route):
    """Маршрут содержит этап без своего блока (напр. «По») — такую деталь «видит склад»."""
    if not route:
        return False
    for tok in _ROUTE_TOKEN_RE.split(str(route).upper()):
        tok = tok.strip()
        if not tok:
            continue
        if tok in ("Г", "ГИБ", "Л", "ЛАЗ", "СВ", "СВАР", "М", "МЕХ"):
            continue
        if tok == "Т" or tok.startswith("ТРУБ"):
            continue
        return True
    return False


def _stage_done(item, stage):
    return sum(c.quantity for c in item.completions if (c.stage or "bender") == stage)


def _item_stages_status(item):
    """По каждой стадии маршрута: выполнено/всего/завершена ли."""
    q = item.quantity
    out = {}
    for s in _route_stages(item.route):
        d = _stage_done(item, s)
        out[s] = {"total": q, "done": min(d, q), "full": d >= q}
    return out


def _stage_full(item, stage):
    return _stage_done(item, stage) >= item.quantity


def _open_stage(item):
    """Первая невыполненная отслеживаемая стадия маршрута (или None, если все выполнены)."""
    for s in _route_stages(item.route):
        if not _stage_full(item, s):
            return s
    return None


def _forbidden(detail: str):
    raise HTTPException(status_code=403, detail=detail)


def _managing(current_user: User = Depends(get_current_user)):
    if current_user.role not in MANAGING_ROLES:
        _forbidden("Только для начальника/администратора")
    return current_user


def _worker(current_user: User = Depends(get_current_user)):
    if current_user.role not in WORKER_ROLES:
        _forbidden("Только для гибщика")
    return current_user


# ---------- Парсинг Excel ----------

KEYWORDS = {
    "order": ["заказ", "договор", "номер заказа", "№ заказа"],
    "name": ["наименовани", "название"],
    "part": ["чертеж", "чертёж", "обознач", "деталь", "номер детали", "артикул"],
    "qty": ["количеств", "кол-во", "кол."],
    "route": ["маршрут", "операци", "тех.процесс", "техпроцесс"],
    "thickness": ["толщин", "толщ"],
    "steel": ["марка", "сталь", "материал", "материал"],
}

FIELD_ORDER = ["part", "qty", "route", "thickness", "steel", "order", "name"]


def _normalize(v):
    if v is None:
        return ""
    return str(v).strip().replace("\u00a0", " ").lower()


_HL_2 = re.compile(r'=HYPERLINK\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)', re.IGNORECASE)
_HL_1 = re.compile(r'=HYPERLINK\(\s*"([^"]*)"\s*,?\s*\)', re.IGNORECASE)


def _url_tail(url):
    t = (url or "").strip()
    t = t.split("#")[-1]
    t = t.rstrip("/").rsplit("/", 1)[-1]
    t = t.rsplit("\\", 1)[-1]
    t = re.sub(r"\.(dwg|pdf|dxf|xlsx?|xls|step|stp|iges)$", "", t, flags=re.I)
    return t.strip()


def _text_of(cell):
    """Текст ячейки с учётом гиперссылок: берёт caption формулы =HYPERLINK("url","caption")."""
    v = cell.value
    if v is None:
        return ""
    s = str(v).strip()
    if s.startswith("="):
        m = _HL_2.match(s)
        if m:
            cap = m.group(2).strip()
            if cap:
                return cap
            return _url_tail(m.group(1))
        m = _HL_1.match(s)
        if m:
            return _url_tail(m.group(1))
    return s


def _is_int(v):
    if v is None or isinstance(v, bool):
        return False
    if isinstance(v, int):
        return True
    if isinstance(v, float):
        return v.is_integer()
    try:
        float(str(v).replace(" ", "").replace("\u00a0", ""))
        return True
    except (ValueError, TypeError):
        return False


def _sp_signature(ws, ws_f):
    """Формат «СП_...» без заголовков: A=номер заказа, D=номер детали, F=количество."""
    if ws.max_column < 11:
        return False
    order_val = None
    d_hits = f_hits = a_ok = n = 0
    for r in range(3, min(ws.max_row, 20) + 1):
        a = ws.cell(row=r, column=1).value
        d = _text_of(ws_f.cell(row=r, column=4))
        f = ws.cell(row=r, column=6).value
        if a is None and d == "" and f is None:
            continue
        n += 1
        try:
            av = int(float(str(a).strip()))
            if order_val is None:
                order_val = av
            elif av == order_val:
                a_ok += 1
        except (ValueError, TypeError):
            pass
        if re.match(r"^\d{4,}\s*-\s*[A-Za-z0-9]+$", d):
            d_hits += 1
        if _is_int(f):
            f_hits += 1
    if n < 5:
        return False
    return d_hits >= n * 0.8 and f_hits >= n * 0.8 and a_ok >= n * 0.6


HEADERLESS_TEMPLATES = [
    {
        "name": "СП-расчёт (гиперссылки)",
        "start_row": 3,
        "columns": {"order": 1, "part": 4, "qty": 6, "thickness": 5, "route": 9, "steel": 11},
        "signature": _sp_signature,
    },
]


def _match_headerless_template(ws, ws_f):
    for t in HEADERLESS_TEMPLATES:
        try:
            if t["signature"](ws, ws_f):
                return t
        except Exception:
            continue
    return None


def _parse_rows(ws, ws_f):
    """Возвращает (заголовок: dict колонка->поле, строки: список (row_index, cells))."""
    header_row = None
    header_map = None
    max_col = ws.max_column
    for r in range(1, min(ws.max_row, 60) + 1):
        cells = [_normalize(ws.cell(row=r, column=c).value) for c in range(1, max_col + 1)]
        non_empty = [c for c in cells if c]
        if len(non_empty) < 3:
            continue
        hit = {kw: False for kw in KEYWORDS}
        for cell in cells:
            for field, words in KEYWORDS.items():
                if any(w in cell for w in words):
                    hit[field] = True
        if hit["qty"] and (hit["route"] or hit["thickness"] or hit["part"]):
            header_row = r
            header_map = {}
            for c in range(1, max_col + 1):
                cell = cells[c - 1]
                if not cell:
                    continue
                for field in FIELD_ORDER:
                    if field in header_map:
                        continue
                    if any(w in cell for w in KEYWORDS[field]):
                        header_map[field] = c
                        break
            if "order" not in header_map:
                header_map["order"] = 1
            break

    is_template = False
    if header_row is None:
        template = _match_headerless_template(ws, ws_f)
        if template is None:
            raise HTTPException(status_code=400, detail="Не удалось найти строку заголовков (нужны: количество, маршрут/толщина)")
        is_template = True
        header_row = template["start_row"]
        header_map = dict(template["columns"])

    rows = []
    start = header_row if is_template else header_row + 1
    for r in range(start, ws.max_row + 1):
        cells = [ws.cell(row=r, column=c).value for c in range(1, max_col + 1)]
        part_col = header_map.get("part")
        part = _text_of(ws_f.cell(row=r, column=part_col)) if part_col else ""
        qty = cells[header_map["qty"] - 1] if "qty" in header_map else None
        if not part and (qty is None or _normalize(qty) == "" or qty == 0):
            continue
        rows.append((r, cells))
    return header_map, rows


def _clean(val, default=""):
    if val is None:
        return default
    s = str(val).strip()
    return s


def _to_int(val):
    if val is None:
        return 0
    try:
        return int(float(str(val).replace(" ", "").replace("\u00a0", "")))
    except (ValueError, TypeError):
        return 0


def _to_float(val):
    if val is None:
        return None
    try:
        f = float(str(val).replace(",", ".").replace(" ", ""))
        return f
    except (ValueError, TypeError):
        return None


class UploadResponse(BaseModel):
    orders: List[dict]


@router.post("/upload", response_model=UploadResponse)
def upload_order(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(_managing),
):
    if not (file.filename or "").lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=400, detail="Нужен файл Excel (.xlsx)")

    try:
        from openpyxl import load_workbook
        from io import BytesIO
        raw = file.file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Пустой файл")
        wb = load_workbook(BytesIO(raw), data_only=True)
        wb_f = load_workbook(BytesIO(raw), data_only=False)
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"UPLOAD_ERR {e!r} name={file.filename!r}")
        raise HTTPException(status_code=400, detail="Не удалось открыть Excel-файл")

    orders_by_number = {}
    for idx, ws in enumerate(wb.worksheets):
        ws_f = wb_f.worksheets[idx]
        try:
            header_map, rows = _parse_rows(ws, ws_f)
        except HTTPException:
            continue
        for r, cells in rows:
            order_number = _clean(cells[header_map["order"] - 1] if "order" in header_map else "")
            if not order_number:
                order_number = "Без номера"
            if order_number not in orders_by_number:
                orders_by_number[order_number] = []
            orders_by_number[order_number].append(cells)

    if not orders_by_number:
        raise HTTPException(status_code=400, detail="В файле нет строк с деталями")

    result = []
    for order_number, row_groups in orders_by_number.items():
        existing = db.query(SpecOrder).filter(SpecOrder.order_number == order_number).first()
        if existing is not None:
            for cells in row_groups:
                _ = cells
            # повторная загрузка того же номера заказа — пропускаем без ошибки
            result.append({
                "order_id": existing.id,
                "order_number": order_number,
                "name": existing.name,
                "items": 0,
                "bending_items": 0,
                "status": "exists",
            })
            continue

        order = SpecOrder(
            order_number=order_number,
            name=f"Заказ {order_number}",
            source_file=file.filename or "",
            created_by=current_user.id,
        )
        db.add(order)
        db.flush()

        items_total = 0
        bending_total = 0
        for cells in row_groups:
            part_col = header_map.get("part")
            part = _text_of(ws_f.cell(row=r, column=part_col)) if part_col else ""
            qty = _to_int(cells[header_map["qty"] - 1])
            route = _clean(cells[header_map["route"] - 1]) if "route" in header_map else ""
            thickness = _to_float(cells[header_map["thickness"] - 1]) if "thickness" in header_map else None
            steel = _clean(cells[header_map["steel"] - 1]) if "steel" in header_map else ""
            needs_bending = 1 if ("Г" in route.upper()) else 0

            db.add(OrderItem(
                order_id=order.id,
                part_number=part,
                quantity=qty,
                thickness=thickness,
                steel_grade=steel,
                route=route,
                needs_bending=needs_bending,
            ))
            items_total += 1
            bending_total += needs_bending

        db.commit()
        db.refresh(order)
        result.append({
            "order_id": order.id,
            "order_number": order_number,
            "name": order.name,
            "items": items_total,
            "bending_items": bending_total,
            "status": "created",
        })
    return {"orders": result}


# ---------- Чтение ----------

def _order_percent(order):
    """Доля выполненных стадий по всем деталям (детали без отслеживаемых стадий — готовы)."""
    total = 0.0
    done = 0.0
    for i in order.items:
        q = float(i.quantity)
        st = _route_stages(i.route)
        if not st:
            total += q
            done += q
            continue
        d_stages = sum(1 for s in st if _stage_done(i, s) >= i.quantity)
        total += q
        done += q * d_stages / len(st)
    if total <= 0:
        return 100
    return int(round(done / total * 100))


def _order_blocks(order, percent):
    """Блоки, в которых заказ сейчас виден."""
    blocks = set()
    for i in order.items:
        for s, st in _item_stages_status(i).items():
            if not st["full"]:
                blocks.add(s)
    untracked = any(_has_untracked_tokens(i.route) for i in order.items)
    if untracked:
        blocks.add(BLOCK_STOREKEEPER)
    if 80 < percent < 100:
        blocks.add(BLOCK_STOREKEEPER)
    return sorted(blocks)


def _order_stages_aggregate(order):
    agg = {}
    for i in order.items:
        for s, st in _item_stages_status(i).items():
            a = agg.setdefault(s, {"total": 0, "done": 0})
            a["total"] += st["total"]
            a["done"] += st["done"]
    return agg


def _order_progress(db: Session, order: SpecOrder):
    items = order.items
    bend_items = [i for i in items if i.needs_bending]
    total_bend = sum(i.quantity for i in bend_items)
    done_bend = 0
    any_open_claim = False
    for i in bend_items:
        done_bend += sum(c.quantity for c in i.completions)
        if any(c.completed_at is None for c in i.claims):
            any_open_claim = True
    in_progress = done_bend > 0 or any_open_claim
    percent = _order_percent(order)
    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "name": order.name,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "ready_at": order.ready_at.isoformat() if order.ready_at else None,
        "total_items": len(items),
        "bending_items": len(bend_items),
        "total_bend_quantity": total_bend,
        "done_bend_quantity": done_bend,
        "remaining_bend_quantity": max(0, total_bend - done_bend),
        "in_progress": in_progress,
        "percent": percent,
        "blocks": _order_blocks(order, percent),
        "stages": _order_stages_aggregate(order),
    }


ARCHIVE_KEEP_DAYS = 365


def purge_expired_archive(db: Session, commit=False):
    """Архив «готов» хранится год, после чего удаляется."""
    cutoff = moscow_now() - timedelta(days=ARCHIVE_KEEP_DAYS)
    expired = (
        db.query(SpecOrder)
        .filter(SpecOrder.status == "ready", SpecOrder.ready_at.isnot(None))
        .filter(SpecOrder.ready_at < cutoff)
        .all()
    )
    deleted = 0
    for o in expired:
        for item in o.items:
            for c in item.completions:
                db.delete(c)
            db.delete(item)
        db.delete(o)
        deleted += 1
    if commit and deleted:
        db.commit()
    return deleted


@router.get("")
def list_orders(
    status: Optional[str] = None,
    block: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in MANAGING_ROLES:
        purge_expired_archive(db, commit=True)
        q = db.query(SpecOrder)
        if status in ("open", "ready"):
            q = q.filter(SpecOrder.status == status)
        if block:
            q = q.filter(SpecOrder.status == "open")
        orders = q.order_by(SpecOrder.created_at.desc()).all()
        result = [_order_progress(db, o) for o in orders]
        if block:
            result = [p for p in result if block in p["blocks"]]
        # заказы в работе — вниз (не тронутые сверху, внутри групп новее — выше)
        result.sort(key=lambda p: p["in_progress"])
        return result

    _worker(current_user)
    orders = (
        db.query(SpecOrder)
        .filter(SpecOrder.status == "open")
        .order_by(SpecOrder.created_at.desc())
        .all()
    )
    result = [_order_progress(db, o) for o in orders]
    result.sort(key=lambda p: p["in_progress"])
    return result


class ItemResponse(BaseModel):
    id: int
    part_number: str
    quantity: int
    thickness: Optional[float]
    steel_grade: str
    route: str
    needs_bending: bool
    done_quantity: int = 0
    remaining: int = 0
    stages: dict = {}
    untracked_route: bool = False
    completions: List[dict] = []
    claim: Optional[dict] = None
    active: bool = True


class OrderDetailResponse(BaseModel):
    order_id: int
    order_number: str
    name: str
    status: str
    created_at: str
    items: List[ItemResponse]


def _claim_response(c: OrderItemClaim) -> dict:
    workers = [{"id": c.worker_id, "name": _user_name(c.worker_id)}]
    for p in sorted([x for x in c.participants if x.status == "accepted"], key=lambda x: x.worker_id):
        workers.append({"id": p.worker_id, "name": _user_name(p.worker_id)})
    pending = [
        {"id": p.worker_id, "name": _user_name(p.worker_id)}
        for p in sorted([x for x in c.participants if x.status == "pending"], key=lambda x: x.worker_id)
    ]
    return {
        "id": c.id,
        "worker_id": c.worker_id,
        "worker_name": _user_name(c.worker_id),
        "claimed_at": c.claimed_at.isoformat(),
        "claimed_at_ms": int(c.claimed_at.timestamp() * 1000),
        "completed_at": c.completed_at.isoformat() if c.completed_at else None,
        "completed_at_ms": int(c.completed_at.timestamp() * 1000) if c.completed_at else None,
        "workers": workers,
        "pending": pending,
    }


def _open_claim_for_item(db, item_id: int):
    return (
        db.query(OrderItemClaim)
        .filter(OrderItemClaim.item_id == item_id, OrderItemClaim.completed_at.is_(None))
        .order_by(OrderItemClaim.claimed_at.desc())
        .first()
    )


def _item_response(item: OrderItem, claim=None) -> dict:
    done = sum(c.quantity for c in item.completions)
    comps = []
    for c in sorted(item.completions, key=lambda x: x.completed_at):
        comps.append({
            "id": c.id,
            "executor_id": c.executor_id,
            "executor_name": _user_name(c.executor_id),
            "marked_by": c.marked_by,
            "marked_by_name": _user_name(c.marked_by),
            "quantity": c.quantity,
            "note": c.note or "",
            "stage": c.stage or "bender",
            "completed_at": c.completed_at.isoformat(),
            "completed_at_ms": int(c.completed_at.timestamp() * 1000),
        })
    if claim is None and item.claims:
        claim = sorted(item.claims, key=lambda x: x.claimed_at, reverse=True)[0]
    return {
        "id": item.id,
        "part_number": item.part_number,
        "quantity": item.quantity,
        "thickness": item.thickness,
        "steel_grade": item.steel_grade or "",
        "route": item.route or "",
        "needs_bending": bool(item.needs_bending),
        "done_quantity": done,
        "remaining": max(0, item.quantity - done),
        "stages": _item_stages_status(item),
        "untracked_route": _has_untracked_tokens(item.route),
        "completions": comps,
        "claim": _claim_response(claim) if claim else None,
    }


_user_name_cache = {}


def _user_name(uid):
    return _user_name_cache.get(uid)


@router.get("/{order_id}", response_model=OrderDetailResponse)
def get_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")

    # загружаем кэш имён всех участников заказов (для отметок)
    for u in db.query(User).filter(User.role.in_(WORKER_ROLES + ["manager", "admin"])).all():
        _user_name_cache[u.id] = u.full_name

    items = sorted(order.items, key=lambda i: (i.needs_bending == 0, i.part_number))
    is_manager = current_user.role in MANAGING_ROLES
    worker_block = None
    if not is_manager:
        _worker(current_user)
        worker_block = current_user.block or "bender"

    responses = [_item_response(i) for i in items]
    if not is_manager:
        # рабочий видит все детали, но активна только та, что сейчас на его этапе
        for i, r in zip(items, responses):
            r["active"] = worker_block in PROD_STAGES and _open_stage(i) == worker_block
    # гибщику: его заявки — сверху, свободные — в середине,
    # взятые другим гибщиком — в самом низу; начальник видит всё (включая выполненные)
    responses.sort(key=lambda r: _item_sort_key(r, current_user.id, is_manager))

    return {
        "order_id": order.id,
        "order_number": order.order_number,
        "name": order.name,
        "status": order.status,
        "created_at": order.created_at.isoformat(),
        "items": responses,
    }


def _item_sort_key(r: dict, user_id: int, is_manager: bool):
    claim = r.get("claim")
    open_claim = bool(claim and claim.get("completed_at") is None)
    if open_claim:
        if not is_manager and user_id != claim.get("worker_id"):
            group = 3  # взял другой гибщик — вниз
        else:
            group = 0  # моя работа / начальник видит всё «в работе» сверху
    else:
        # свободные и выполненные — вместе, по порядку чертежа; выполненные
        # помечаются «✅ ГОТОВО» и остаются видимыми, а не уходят в самый низ
        group = 1
    return (group, r["part_number"])


# ---------- Отметки ----------

class CompleteRequest(BaseModel):
    quantity: int
    executor_id: Optional[int] = None
    note: str = ""
    stage: Optional[str] = None


def _block_stage(user):
    b = user.block or "bender"
    return b if b in PROD_STAGES else None


def _auto_ready(db: Session, order: SpecOrder):
    """Заказ выполнен (100% по всем стадиям, без «складских» маршрутов) — уходит в архив."""
    if order.status != "open":
        return
    if _order_percent(order) >= 100 and not any(_has_untracked_tokens(i.route) for i in order.items):
        order.status = "ready"
        order.ready_at = moscow_now()
        db.commit()


@router.post("/{order_id}/items/{item_id}/complete")
def complete_item(
    order_id: int,
    item_id: int,
    body: CompleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != "open":
        raise HTTPException(status_code=400, detail="Заказ закрыт")
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Деталь не найдена")
    if body.quantity <= 0:
        raise HTTPException(status_code=400, detail="Количество должно быть больше нуля")

    stage = (body.stage or ("bender" if item.needs_bending else None)) or "bender"
    item_stages = _route_stages(item.route)
    if stage not in item_stages:
        raise HTTPException(status_code=400, detail="По маршруту детали нет такого этапа")

    is_manager = current_user.role in MANAGING_ROLES
    if not is_manager:
        if stage == "trubo":
            _forbidden("Стадию «Труборез» отмечает руководитель")
        allowed = _block_stage(current_user)
        if stage != allowed:
            _forbidden("Вы можете отмечать только этап своего участка")
        # строго по маршруту: деталь доступна только на текущей стадии
        if _open_stage(item) != allowed:
            o = _open_stage(item)
            if o is None:
                _forbidden("Деталь выполнена полностью по всем этапам")
            _forbidden(f"Сначала выполните этап «{STAGE_NAMES.get(o, o)}»")

    if current_user.role in WORKER_ROLES:
        executor_id = current_user.id
    else:
        if not body.executor_id:
            raise HTTPException(status_code=400, detail="Укажите фактического исполнителя")
        executor_id = body.executor_id
        executor = db.query(User).filter(User.id == executor_id).first()
        if not executor or executor.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Исполнитель должен быть рабочим")

    done = _stage_done(item, stage)
    new_done = done + body.quantity
    if new_done > item.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Превышение количества по этапу: выполнено {done}, осталось {max(0, item.quantity - done)}",
        )

    # деталь «занята» другим гибщиком — по ней нельзя отмечать без переназначения
    if stage == "bender" and current_user.role in WORKER_ROLES:
        open_claim = _open_claim_for_item(db, item.id)
        if open_claim:
            allowed = {open_claim.worker_id}
            allowed.update(p.worker_id for p in open_claim.participants)
            if executor_id not in allowed:
                raise HTTPException(
                    status_code=400,
                    detail=f"Деталь сейчас взял(а): {_user_name(open_claim.worker_id)}",
                )
    else:
        open_claim = None

    completion = OrderItemCompletion(
        item_id=item.id,
        executor_id=executor_id,
        marked_by=current_user.id,
        quantity=body.quantity,
        note=body.note,
        stage=stage,
    )
    db.add(completion)
    # «Закончили исполнение»: заявка закрывается, когда деталь выполнена
    # полностью; иначе (legacy-пометка без заявки) фиксируется с временем.
    if stage == "bender":
        now = moscow_now()
        if open_claim:
            if new_done >= item.quantity:
                open_claim.completed_at = now
        elif new_done >= item.quantity:
            db.add(OrderItemClaim(
                item_id=item.id,
                worker_id=executor_id,
                claimed_at=now,
                completed_at=now,
            ))
    db.commit()
    db.refresh(completion)
    _auto_ready(db, order)
    return {"id": completion.id, "status": "completed"}


# ---------- «Взял в работу» ----------

class ClaimRequest(BaseModel):
    executor_id: Optional[int] = None


@router.post("/{order_id}/items/{item_id}/claim")
def claim_item(
    order_id: int,
    item_id: int,
    body: ClaimRequest = ClaimRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Гибщик берёт деталь в работу; начальник может назначить исполнителя."""
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != "open":
        raise HTTPException(status_code=400, detail="Заказ закрыт")
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Деталь не найдена")
    if not item.needs_bending:
        raise HTTPException(status_code=400, detail="По этой детали гибка не предусмотрена маршрутом")
    done = sum(c.quantity for c in item.completions)
    if done >= item.quantity:
        raise HTTPException(status_code=400, detail="Деталь уже выполнена полностью")

    if current_user.role in WORKER_ROLES:
        worker_id = current_user.id
        if _open_stage(item) != "bender":
            o = _open_stage(item)
            if o is None:
                raise HTTPException(status_code=400, detail="Деталь уже выполнена полностью")
            raise HTTPException(status_code=400, detail=f"Деталь сейчас на этапе «{STAGE_NAMES.get(o, o)}»")
    else:
        if not body.executor_id:
            raise HTTPException(status_code=400, detail="Укажите исполнителя")
        worker_id = body.executor_id
        executor = db.query(User).filter(User.id == worker_id).first()
        if not executor or executor.role not in WORKER_ROLES:
            raise HTTPException(status_code=400, detail="Исполнитель должен быть гибщиком")

    open_claim = _open_claim_for_item(db, item.id)
    if open_claim:
        if open_claim.worker_id == worker_id:
            _user_name_cache[worker_id] = open_claim.worker.full_name
            return _claim_response(open_claim)
        if current_user.role in WORKER_ROLES:
            _user_name_cache[open_claim.worker_id] = open_claim.worker.full_name
            raise HTTPException(
                status_code=400,
                detail=f"Деталь уже взял(а): {_user_name(open_claim.worker_id)}",
            )
        # начальник переназначает: прежняя заявка закрывается
        open_claim.completed_at = moscow_now()

    claim = OrderItemClaim(item_id=item.id, worker_id=worker_id, claimed_at=moscow_now())
    wname = db.query(User).filter(User.id == worker_id).first()
    _user_name_cache[worker_id] = wname.full_name if wname else "?"
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return _claim_response(claim)


@router.delete("/{order_id}/items/{item_id}/claim")
def release_claim(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Гибщик отказывается от гибки: открытая заявка снимается, деталь снова доступна."""
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != "open":
        raise HTTPException(status_code=400, detail="Заказ закрыт")
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Деталь не найдена")
    open_claim = _open_claim_for_item(db, item.id)
    if not open_claim:
        raise HTTPException(status_code=404, detail="Деталь не в работе")
    if current_user.role in WORKER_ROLES and open_claim.worker_id != current_user.id:
        _user_name_cache[open_claim.worker_id] = open_claim.worker.full_name
        raise HTTPException(
            status_code=400,
            detail=f"Деталь в работе у: {_user_name(open_claim.worker_id)}",
        )
    worker_name = open_claim.worker.full_name
    db.delete(open_claim)
    db.commit()
    return {"ok": True, "detail": f"Гибщик {worker_name} отказался от детали"}


# ---------- Соисполнители ----------

def _claim_for_open_item(db, order_id: int, item_id: int, current_user) -> OrderItemClaim:
    """Общая проверка: заказ открыт, деталь в работе; возвращает открытую заявку."""
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    if order.status != "open":
        raise HTTPException(status_code=400, detail="Заказ закрыт")
    item = db.query(OrderItem).filter(OrderItem.id == item_id, OrderItem.order_id == order_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Деталь не найдена")
    open_claim = _open_claim_for_item(db, item.id)
    if not open_claim:
        raise HTTPException(status_code=400, detail="Деталь не в работе")
    if current_user.role in WORKER_ROLES and open_claim.worker_id != current_user.id:
        _user_name_cache[open_claim.worker_id] = open_claim.worker.full_name
        raise HTTPException(
            status_code=400,
            detail=f"Состав бригады меняет только взявший: {_user_name(open_claim.worker_id)}",
        )
    return open_claim


@router.post("/{order_id}/items/{item_id}/claim/participants")
def add_claim_participant(
    order_id: int,
    item_id: int,
    body: ClaimRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Взявший деталь (или начальник) добавляет соисполнителя."""
    if not body.executor_id:
        raise HTTPException(status_code=400, detail="Укажите сотрудника")
    open_claim = _claim_for_open_item(db, order_id, item_id, current_user)

    done = sum(c.quantity for c in open_claim.item.completions)
    if done >= open_claim.item.quantity:
        raise HTTPException(status_code=400, detail="Деталь уже выполнена полностью")

    worker = db.query(User).filter(User.id == body.executor_id).first()
    if not worker:
        raise HTTPException(status_code=400, detail="Сотрудник не найден")
    if worker.id == open_claim.worker_id:
        raise HTTPException(status_code=400, detail="Это основной гибщик")
    existing = (
        db.query(OrderItemClaimWorker)
        .filter(
            OrderItemClaimWorker.claim_id == open_claim.id,
            OrderItemClaimWorker.worker_id == worker.id,
        )
        .first()
    )
    if existing and existing.status in ("pending", "accepted"):
        # повторное сохранение — просто возвращаем текущее состояние (идемпотентно)
        _user_name_cache[worker.id] = worker.full_name
        _user_name_cache[open_claim.worker_id] = open_claim.worker.full_name if open_claim.worker else None
        db.refresh(open_claim)
        return _claim_response(open_claim)
    if existing:
        existing.status = "pending"
        existing.invited_by = current_user.id
        existing.invited_at = moscow_now()
        existing.responded_at = None
    else:
        db.add(OrderItemClaimWorker(
            claim_id=open_claim.id,
            worker_id=worker.id,
            invited_by=current_user.id,
            status="pending",
            invited_at=moscow_now(),
        ))
    _user_name_cache[worker.id] = worker.full_name
    _user_name_cache[open_claim.worker_id] = open_claim.worker.full_name if open_claim.worker else None
    db.commit()
    db.refresh(open_claim)
    return _claim_response(open_claim)


@router.delete("/{order_id}/items/{item_id}/claim/participants/{worker_id}")
def remove_claim_participant(
    order_id: int,
    item_id: int,
    worker_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Взявший деталь (или начальник) убирает соисполнителя."""
    open_claim = _claim_for_open_item(db, order_id, item_id, current_user)
    if worker_id == open_claim.worker_id:
        raise HTTPException(status_code=400, detail="Нельзя убрать основного гибщика")
    part = (
        db.query(OrderItemClaimWorker)
        .filter(OrderItemClaimWorker.claim_id == open_claim.id, OrderItemClaimWorker.worker_id == worker_id)
        .first()
    )
    if not part:
        raise HTTPException(status_code=404, detail="Такого соисполнителя нет")
    db.delete(part)
    db.commit()
    db.refresh(open_claim)
    return _claim_response(open_claim)


@router.delete("/completions/{completion_id}")
def delete_completion(
    completion_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    c = db.query(OrderItemCompletion).filter(OrderItemCompletion.id == completion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Отметка не найдена")
    if current_user.role not in MANAGING_ROLES and c.marked_by != current_user.id:
        _forbidden("Можно удалять только свои отметки")
    db.delete(c)
    db.commit()
    return {"status": "deleted"}


# ---------- Закрытие / архив / удаление ----------

@router.post("/{order_id}/close")
def close_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(_managing)):
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = "closed"
    db.commit()
    return {"status": "closed"}


@router.post("/{order_id}/ready")
def mark_ready(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(_managing)):
    """Начальник отмечает заказ готовым — уходит в архив, хранится год."""
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    order.status = "ready"
    order.ready_at = moscow_now()
    db.commit()
    return {"status": "ready"}


@router.delete("/{order_id}")
def delete_order(order_id: int, db: Session = Depends(get_db), current_user: User = Depends(_managing)):
    """Начальник удаляет заказ (вместе с позициями и отметками о гибке)."""
    order = db.query(SpecOrder).filter(SpecOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Заказ не найден")
    for item in order.items:
        for c in item.completions:
            db.delete(c)
    for item in order.items:
        db.delete(item)
    db.delete(order)
    db.commit()
    return {"status": "deleted"}


# ---------- Статистика ----------

class OrderStat(BaseModel):
    worker_id: int
    worker_name: str
    total_bent_quantity: int
    marks: int
    distinct_parts: int


@router.get("/stats/my")
def my_order_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = (
        db.query(
            OrderItemCompletion.executor_id,
            func.sum(OrderItemCompletion.quantity),
            func.count(OrderItemCompletion.id),
            func.count(func.distinct(OrderItem.id)),
        )
        .join(OrderItem, OrderItem.id == OrderItemCompletion.item_id)
        .filter(OrderItemCompletion.executor_id == current_user.id)
        .group_by(OrderItemCompletion.executor_id)
    )
    if date_from:
        q = q.filter(OrderItemCompletion.completed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(OrderItemCompletion.completed_at <= datetime.combine(date_to, datetime.max.time()))

    row = q.first()
    if row is None:
        return OrderStat(
            worker_id=current_user.id,
            worker_name=current_user.full_name or current_user.username,
            total_bent_quantity=0,
            marks=0,
            distinct_parts=0,
        )
    executor_id, total, marks, parts = row
    return OrderStat(
        worker_id=executor_id,
        worker_name=current_user.full_name or current_user.username,
        total_bent_quantity=int(total or 0),
        marks=int(marks or 0),
        distinct_parts=int(parts or 0),
    )


@router.get("/stats/list")
def order_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    worker_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(_managing),
):
    q = (
        db.query(
            OrderItemCompletion.executor_id,
            func.sum(OrderItemCompletion.quantity),
            func.count(OrderItemCompletion.id),
            func.count(func.distinct(OrderItem.id)),
        )
        .join(OrderItem, OrderItem.id == OrderItemCompletion.item_id)
        .group_by(OrderItemCompletion.executor_id)
    )
    if date_from:
        q = q.filter(OrderItemCompletion.completed_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(OrderItemCompletion.completed_at <= datetime.combine(date_to, datetime.max.time()))
    if worker_id:
        q = q.filter(OrderItemCompletion.executor_id == worker_id)

    result = []
    for executor_id, total, marks, parts in q.all():
        executor = db.query(User).filter(User.id == executor_id).first()
        result.append(OrderStat(
            worker_id=executor_id,
            worker_name=executor.full_name if executor else "?",
            total_bent_quantity=int(total or 0),
            marks=int(marks or 0),
            distinct_parts=int(parts or 0),
        ))
    result.sort(key=lambda x: -x.total_bent_quantity)
    return result