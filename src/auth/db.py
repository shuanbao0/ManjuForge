"""SQLAlchemy engine + session for the auth/users database."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker

from .instance import get_db_path

logger = logging.getLogger(__name__)

Base = declarative_base()

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _create_engine() -> Engine:
    db_path = get_db_path()
    url = f"sqlite:///{db_path}"
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 30},
        future=True,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _record):  # noqa: ANN001
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    return engine


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _create_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        # Import models so Base.metadata sees them, then create.
        from . import models  # noqa: F401  (registers tables with Base)

        Base.metadata.create_all(_engine)
        logger.info("Auth DB ready at %s", get_db_path())
    return _engine


def get_session_factory() -> sessionmaker:
    if _SessionLocal is None:
        get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


@contextmanager
def session_scope() -> Iterator[scoped_session]:
    """Context manager session for non-FastAPI callers (tests, scripts)."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_for_tests() -> None:
    """Tear down the engine — only for pytest fixtures."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _SessionLocal = None
