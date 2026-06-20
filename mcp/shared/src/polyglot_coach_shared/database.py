import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
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


def get_engine(db_path: str | None = None):
    url = _make_url(db_path)
    if url not in _engine_cache:
        _engine_cache[url] = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return _engine_cache[url]


def init_db(db_path: str | None = None):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def get_session(db_path: str | None = None):
    engine = init_db(db_path)
    return scoped_session(sessionmaker(bind=engine))
