from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey, BigInteger


class Base(DeclarativeBase):
    pass


class ApiKey(Base):
    __tablename__ = "api_keys"
    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    template: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    token_profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    app_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("apps.id"), nullable=True)
    token_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tokens.id"), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class App(Base):
    __tablename__ = "apps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ApiKeyTool(Base):
    __tablename__ = "api_key_tools"
    key: Mapped[str] = mapped_column(String(200), ForeignKey("api_keys.key"), primary_key=True)
    tool: Mapped[str] = mapped_column(String(200), primary_key=True)

class Group(Base):
    __tablename__ = "groups"
    name: Mapped[str] = mapped_column(String(100), primary_key=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

class GroupTool(Base):
    __tablename__ = "group_tools"
    group: Mapped[str] = mapped_column(String(100), ForeignKey("groups.name"), primary_key=True)
    tool: Mapped[str] = mapped_column(String(200), primary_key=True)

class GroupTag(Base):
    __tablename__ = "group_tags"
    group: Mapped[str] = mapped_column(String(100), ForeignKey("groups.name"), primary_key=True)
    tag: Mapped[str] = mapped_column(String(100), primary_key=True)

class ApiKeyGroup(Base):
    __tablename__ = "api_key_groups"
    key: Mapped[str] = mapped_column(String(200), ForeignKey("api_keys.key"), primary_key=True)
    group: Mapped[str] = mapped_column(String(100), ForeignKey("groups.name"), primary_key=True)


    


class Token(Base):
    __tablename__ = "tokens"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Logical name to identify token row (e.g., user-id or profile name). Unique for convenience.
    profile: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    # OAuth token payload (flattened fields only)
    access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_on: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    expires_in: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    token_type: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    scope: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # App meta
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    client_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    scopes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
