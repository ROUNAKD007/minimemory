from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import secrets

from ..database import get_db
from ..models import ApiKeyORM, hash_key
from ..auth_utils import get_current_user_id

router = APIRouter(prefix="/keys", tags=["api-keys"])

@router.post("", summary="Create a new API key")
def create_key(db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    plaintext = "mmk_" + secrets.token_urlsafe(32)   # show once
    row = ApiKeyORM(owner_id=owner_id, key_hash=hash_key(plaintext))
    db.add(row); db.commit(); db.refresh(row)
    return {"api_key": plaintext, "id": row.id}

@router.get("", summary="List my API keys")
def list_keys(db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    rows = db.query(ApiKeyORM).filter(ApiKeyORM.owner_id == owner_id).all()
    return [{"id": r.id, "active": r.active, "created_at": r.created_at} for r in rows]

@router.delete("/{key_id}", status_code=204)
def revoke_key(key_id: int, db: Session = Depends(get_db), owner_id: int = Depends(get_current_user_id)):
    row = db.query(ApiKeyORM).filter(ApiKeyORM.id == key_id, ApiKeyORM.owner_id == owner_id).first()
    if not row:
        raise HTTPException(404, "Key not found")
    row.active = False
    db.commit()
