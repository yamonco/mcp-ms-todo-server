from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey, Boolean


class Base(DeclarativeBase):
    pass


# Core domain tables (apps/tokens/api_keys) — minimal set to enable X-API-Key and token management


class App(Base):
    __tablename__ = "apps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_secret: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # epoch seconds
    token_endpoint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    app_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("apps.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ApiKey(Base):
    __tablename__ = "api_keys"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    groups: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # list[str]
    token_profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tokens.id"), nullable=True)
    app_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("apps.id"), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# Casbin policy rule table (for DB-backed policies)
class CasbinRule(Base):
    __tablename__ = "casbin_rule"
    # ptype: e.g., "p" (policy) or "g" (group/role)
    ptype: Mapped[str] = mapped_column(String(100), primary_key=True)
    v0: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
    v1: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
    v2: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
    v3: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
    v4: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
    v5: Mapped[Optional[str]] = mapped_column(String(256), nullable=True, primary_key=True)
