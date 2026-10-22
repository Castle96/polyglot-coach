import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from polyglot_coach_shared.models import Base

MEMORY_URL = "sqlite://"

_engine_cache: dict[str, object] = {}
_DEFAULT_PATH = str(Path.home() / ".polyglot-coach" / "data.db")


def _default_db_path() -> str:
    return os.environ.get("POLYGLOT_DB_PATH") or _DEFAULT_PATH


def _make_url(db_path: str | None) -> str:
    resolved = db_path or _default_db_path()
    if resolved == ":memory:":
        return MEMORY_URL
    path = Path(resolved)
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def _configure_sqlite(engine) -> None:
    """Apply pragmas that matter for a local, multi-threaded SQLite file."""

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_connection, _connection_record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        # Foreign keys stay off: curriculum vocabulary rows use profile_id=0 as a
        # sentinel and the model has no system profile row.
        cursor.close()


def get_engine(db_path: str | None = None):
    url = _make_url(db_path)
    if url not in _engine_cache:
        if url == MEMORY_URL:
            # A single shared connection is required so every thread sees the
            # same in-memory database. File databases must not share one.
            engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            engine = create_engine(url, connect_args={"check_same_thread": False})
            _configure_sqlite(engine)
        _engine_cache[url] = engine
    return _engine_cache[url]


def init_db(db_path: str | None = None):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path: str | None = None) -> Session:
    """Create a session. Callers are responsible for closing it.

    Prefer :func:`session_scope`, which always commits or rolls back and closes.
    """
    engine = init_db(db_path)
    return sessionmaker(bind=engine)()


@contextmanager
def session_scope(db_path: str | None = None):
    """Yield a session and guarantee commit/rollback plus close."""
    session = get_session(db_path)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
