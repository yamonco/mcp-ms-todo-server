from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey, BigInteger


class Base(DeclarativeBase):
    pass


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    tools: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class ApiKey(Base):
    __tablename__ = "api_keys"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    template: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    allowed_tools: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    token_profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tokens.id"), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Logical name to identify token row (e.g., user-id or profile name). Unique for convenience.
    profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    # OAuth token payload (flattened fields for queries + raw for future-proofing)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_on: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    expires_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # App meta
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
