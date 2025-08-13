from __future__ import annotations

from typing import Optional, List, Dict, Any
from datetime import datetime
import hashlib
import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey,
    UniqueConstraint, Index, Integer
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import func


class Base(DeclarativeBase):
    pass


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ApiKeyORM(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    api_key: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    plan: Mapped[Optional[str]] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class MemoryORM(Base):
    __tablename__ = "memories"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # optional namespacing (per app/user/agent)
    space: Mapped[str] = mapped_column(String(120), nullable=False, server_default="default", index=True)

    # KV convenience key (unique per owner+space)
    key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    title: Mapped[str] = mapped_column(String(200), nullable=False, server_default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")

    tags: Mapped[List[str]] = mapped_column(JSONB, nullable=False, default=list)

    # NOTE: 'metadata' is reserved by SQLAlchemy. Use 'meta' attribute, map to DB column 'metadata'.
    meta: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, nullable=False, default=dict)

    is_long_term: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("owner_id", "space", "key", name="ux_mem_owner_space_key"),
        Index("ix_mem_owner_space_created", "owner_id", "space", "created_at"),
    )


class ImportJobORM(Base):
    __tablename__ = "import_jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_text: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
