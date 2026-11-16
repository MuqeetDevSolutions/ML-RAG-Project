"""
Database session management.

Ek global engine banate hain aur SQLAlchemy ka sessionmaker use karke
per-request sessions dete hain.

`init_db()` app startup par call hoti hai — tables create karti hai
(agar pehle se nahi hain).
"""

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import settings
from app.db.models import Base


# ----------------------------------------------------------------
# Engine
# ----------------------------------------------------------------

def _build_engine():
    """
    SQLite engine banao.

    check_same_thread=False: FastAPI multiple threads use kar sakta hai;
    SQLite by default same thread check karta hai — hum usay disable
    kar rahe hain (SQLAlchemy internally safe handling karti hai).
    """
    url = settings.DATABASE_URL
    # Ensure data/ folder mojood hai (SQLite file create karne ke liye)
    Path(settings.PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
        echo=False,  # True karo to SQL statements print honge (debug)
        future=True,
    )
    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


# ----------------------------------------------------------------
# Table creation
# ----------------------------------------------------------------

def init_db() -> None:
    """Saari tables create karo (agar nahi hain). Idempotent."""
    Base.metadata.create_all(bind=engine)


# ----------------------------------------------------------------
# Dependency / context manager
# ----------------------------------------------------------------

def get_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency ya context manager ke tor par use karo:

        with next(get_session()) as s: ...
    ya FastAPI me:
        def route(db: Session = Depends(get_session)): ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()