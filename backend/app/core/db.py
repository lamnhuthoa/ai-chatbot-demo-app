from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.settings import get_database_settings


class Base(DeclarativeBase):
    pass


def _make_engine_url() -> str:
    db = get_database_settings()
    return db.DATABASE_URL


engine = create_engine(_make_engine_url(), pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
