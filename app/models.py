from __future__ import annotations
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, JSON, Integer, ForeignKey, BigInteger


class Base(DeclarativeBase):
    pass


# Removed legacy API key, token, app, and group tables in favor of external IdP (authentik)


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
