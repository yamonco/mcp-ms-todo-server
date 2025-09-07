from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import cfg


_engine = None
_SessionLocal = None


def get_engine():
    global _engine, _SessionLocal
    if not cfg.db_url:
        return None
    if _engine is None:
        _engine = create_engine(cfg.db_url, echo=cfg.db_echo, future=True)
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
    return _engine


@contextmanager
def get_session() -> Iterator[Session]:
    if not cfg.db_url:
        raise RuntimeError("DB_URL not configured")
    get_engine()
    assert _SessionLocal is not None
    session: Session = _SessionLocal()  # type: ignore
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ensure_schema(Base) -> None:
    if not cfg.db_url or not cfg.db_auto_create:
        return
    eng = get_engine()
    if eng is not None:
        Base.metadata.create_all(eng)

