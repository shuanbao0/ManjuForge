"""SQLAlchemy engine + session for the auth/users database."""

from __future__ import annotations

import logging
import os
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


def _resolve_database_url() -> str:
    """Pick the SQLAlchemy URL.

    Priority: explicit `DATABASE_URL` env (e.g. `postgresql+psycopg2://...`),
    else SQLite at the instance data dir.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if url:
        # Common shorthand `postgres://` is rejected by SQLAlchemy 2.x.
        if url.startswith("postgres://"):
            url = "postgresql+psycopg2://" + url[len("postgres://"):]
        elif url.startswith("postgresql://") and "+psycopg" not in url:
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        return url
    return f"sqlite:///{get_db_path()}"


def _create_engine() -> Engine:
    url = _resolve_database_url()
    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
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

    # Server-side databases (Postgres, MySQL, ...): use a real connection
    # pool with pre-ping so dropped connections recover automatically.
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=int(os.getenv("DATABASE_POOL_SIZE", "5")),
        max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", "10")),
        pool_recycle=int(os.getenv("DATABASE_POOL_RECYCLE", "1800")),
        future=True,
    )
    return engine


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _create_engine()
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)
        # Import models so Base.metadata sees them, then create.
        from . import models  # noqa: F401  (registers tables with Base)

        Base.metadata.create_all(_engine)
        # Hide credentials when logging the resolved URL.
        try:
            url_repr = str(_engine.url.render_as_string(hide_password=True))
        except Exception:  # noqa: BLE001
            url_repr = "<sqlalchemy url>"
        logger.info("Auth DB ready at %s", url_repr)
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
