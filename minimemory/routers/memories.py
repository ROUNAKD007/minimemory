# minimemory/routers/memories.py
from typing import List, Optional
from datetime import datetime
import io, csv, json, os, uuid
from tempfile import NamedTemporaryFile
from ..auth_utils import get_owner_id

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import get_db, SessionLocal
from ..models import MemoryORM, ImportJobORM
from ..schemas import MemoryCreate, MemoryUpdate, MemoryOut
from ..auth_utils import get_current_user_id

router = APIRouter(prefix="/memories", tags=["memories"])
BATCH_SIZE = 1000

# ---------- helpers ----------
def _get_owned(db: Session, owner_id: int, memory_id: int) -> MemoryORM:
    row = db.query(MemoryORM).filter(
        MemoryORM.id == memory_id,
        MemoryORM.owner_id == owner_id
    ).first()
    if not row:
        raise HTTPException(status_code=404, detail="Memory not found")
    return row

# ---------- list/search ----------
@router.get("", response_model=List[MemoryOut])
def list_memories(
    tag: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    owner_id: int = Depends(get_owner_id)
):
    qry = db.query(MemoryORM).filter(MemoryORM.owner_id == owner_id).order_by(MemoryORM.id.asc())
    if tag:
        qry = qry.filter(MemoryORM.tags.contains([tag]))   # JSONB contains
    if q:
        # uses search_tsv index if you ran the FTS SQL
        qry = qry.filter(text("search_tsv @@ plainto_tsquery('english', :q)")).params(q=q)
    return qry.all()

# ---------- export BEFORE /{memory_id} to avoid conflicts ----------
@router.get("/export")
def export_memories(
    format: str = "json",
    tag: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    owner_id: int = Depends(get_current_user_id),
):
    qry = db.query(MemoryORM).filter(MemoryORM.owner_id == owner_id).order_by(MemoryORM.id.asc())
    if tag:
        qry = qry.filter(MemoryORM.tags.contains([tag]))
    if q:
        qry = qry.filter(text("search_tsv @@ plainto_tsquery('english', :q)")).params(q=q)
    rows = qry.all()

    if format.lower() == "csv":
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id","title","content","tags","is_long_term","created_at"])
        for r in rows:
            w.writerow([r.id, r.title, r.content, json.dumps(r.tags),
                        getattr(r, "is_long_term", True), r.created_at.isoformat()])
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="memories.csv"'},
        )

    # default JSON
    return [
        {
            "id": r.id,
            "title": r.title,
            "content": r.content,
            "tags": r.tags,
            "is_long_term": getattr(r, "is_long_term", True),
            "created_at": r.created_at,
            "owner_id": r.owner_id,
        } for r in rows
    ]

# ---------- import (background task) ----------
def _process_import_file(tmp_path: str, owner_id: int, job_id: uuid.UUID):
    db = SessionLocal()
    try:
        job = db.get(ImportJobORM, job_id)
        if not job:
            return
        job.status = "running"; db.commit()

        created = 0
        batch: list[MemoryORM] = []

        def flush():
            nonlocal created, batch, db, job
            if not batch: return
            db.add_all(batch)
            db.commit()
            created += len(batch)
            batch.clear()
            job.imported_count = created
            db.commit()

        lower = tmp_path.lower()
        if lower.endswith(".csv"):
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for rec in reader:
                    tags = json.loads(rec.get("tags","[]")) if rec.get("tags") else []
                    ilt = rec.get("is_long_term")
                    is_long_term = (str(ilt).lower() != "false") if ilt is not None else True
                    batch.append(MemoryORM(
                        owner_id=owner_id,
                        title=rec.get("title",""),
                        content=rec.get("content",""),
                        tags=tags,
                        is_long_term=is_long_term,
                    ))
                    if len(batch) >= BATCH_SIZE: flush()
                flush()

        elif lower.endswith(".ndjson") or lower.endswith(".jsonl"):
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    d = json.loads(line)
                    batch.append(MemoryORM(
                        owner_id=owner_id,
                        title=d.get("title",""),
                        content=d.get("content",""),
                        tags=d.get("tags", []),
                        is_long_term=d.get("is_long_term", True),
                    ))
                    if len(batch) >= BATCH_SIZE: flush()
                flush()

        else:
            with open(tmp_path, "r", encoding="utf-8", errors="ignore") as f:
                docs = json.load(f)
            if isinstance(docs, dict): docs = [docs]
            for d in docs or []:
                batch.append(MemoryORM(
                    owner_id=owner_id,
                    title=d.get("title",""),
                    content=d.get("content",""),
                    tags=d.get("tags", []),
                    is_long_term=d.get("is_long_term", True),
                ))
                if len(batch) >= BATCH_SIZE: flush()
            flush()

        job.status = "done"
        job.imported_count = created
        job.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        job = db.get(ImportJobORM, job_id)
        if job:
            job.status = "error"
            job.error_text = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()
        try: os.remove(tmp_path)
        except Exception: pass

@router.post("/import", status_code=202)
async def import_memories(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    owner_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    suffix = os.path.splitext(file.filename or "")[1] or ".json"
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            tmp.write(chunk)
        tmp_path = tmp.name

    job = ImportJobORM(owner_id=owner_id, filename=file.filename or os.path.basename(tmp_path))
    db.add(job); db.commit(); db.refresh(job)

    background_tasks.add_task(_process_import_file, tmp_path, owner_id, job.id)
    return {"job_id": str(job.id), "status": "accepted"}

@router.get("/import/{job_id}")
def import_status(job_id: uuid.UUID, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    job = db.get(ImportJobORM, job_id)
    if not job or job.owner_id != owner_id:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": str(job.id),
        "status": job.status,
        "imported_count": job.imported_count,
        "error": job.error_text,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
    }

# ---------- CRUD ----------
@router.post("", response_model=MemoryOut, status_code=201)
def create_memory(payload: MemoryCreate, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    row = MemoryORM(
        owner_id=owner_id,
        title=payload.title,
        content=payload.content,
        tags=payload.tags,
        is_long_term=getattr(payload, "is_long_term", True),
    )
    db.add(row); db.commit(); db.refresh(row)
    return row

@router.get("/{memory_id}", response_model=MemoryOut)
def get_memory(memory_id: int, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    return _get_owned(db, owner_id, memory_id)

@router.put("/{memory_id}", response_model=MemoryOut)
def update_memory(memory_id: int, payload: MemoryUpdate, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    row = _get_owned(db, owner_id, memory_id)
    if payload.title is not None: row.title = payload.title
    if payload.content is not None: row.content = payload.content
    if payload.tags is not None: row.tags = payload.tags
    if getattr(payload, "is_long_term", None) is not None:
        row.is_long_term = payload.is_long_term
    db.commit(); db.refresh(row)
    return row

@router.delete("/{memory_id}", status_code=204)
def delete_memory(memory_id: int, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    row = _get_owned(db, owner_id, memory_id)
    db.delete(row); db.commit()
    return
