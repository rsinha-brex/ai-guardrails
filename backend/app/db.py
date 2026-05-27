from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
# Supabase's transaction-mode pooler (port 6543) reuses underlying connections
# across sessions, which collides with psycopg's prepared-statement cache
# (DuplicatePreparedStatement: "_pg3_0" already exists). Disabling prepared
# statements at the connection level is the standard fix.
engine = create_engine(
    _settings.sync_database_url,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
    future=True,
    connect_args={"prepare_threshold": None},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_session() -> Iterator[Session]:
    """FastAPI dependency that yields a SQLAlchemy session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context-manager flavor for non-request code (seeders, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def ping() -> bool:
    """Cheap connectivity probe used by /health."""
    with engine.connect() as conn:
        return conn.execute(text("select 1")).scalar() == 1
