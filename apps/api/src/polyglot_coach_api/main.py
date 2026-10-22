from contextlib import asynccontextmanager

import logging
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text as db_text

from pathlib import Path

from polyglot_coach_api.data.loader import CURRICULUM_ROOT, load_all_curriculum_data
from polyglot_coach_api.routers import (
    analytics,
    conversation,
    curriculum,
    dictionary,
    grammar,
    learner,
    locale,
    meta,
    review,
    speech,
    tutor,
)
from polyglot_coach_shared.database import session_scope
from polyglot_coach_api.services.llm import is_llm_available
from polyglot_coach_api.services.stt import is_stt_available
from polyglot_coach_api.services.tts import is_tts_available

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=os.environ.get("POLYGLOT_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all_curriculum_data()
    yield


app = FastAPI(
    title="Polyglot Coach API",
    version="0.1.0",
    lifespan=lifespan,
)

_CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("POLYGLOT_CORS_ORIGINS", "*").split(",")
    if origin.strip()
]
_CORS_WILDCARD = _CORS_ORIGINS == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    # Browsers reject credentialed requests when the origin is "*".
    allow_credentials=not _CORS_WILDCARD,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(learner.router, prefix="/api/v1/learner", tags=["learner"])
app.include_router(meta.router, prefix="/api/v1/meta", tags=["meta"])
app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["curriculum"])
app.include_router(dictionary.router, prefix="/api/v1/dictionary", tags=["dictionary"])
app.include_router(grammar.router, prefix="/api/v1/grammar", tags=["grammar"])
app.include_router(locale.router, prefix="/api/v1/locale", tags=["locale"])
app.include_router(conversation.router, prefix="/api/v1/conversation", tags=["conversation"])
app.include_router(review.router, prefix="/api/v1/review", tags=["review"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(speech.router, prefix="/api/v1/speech", tags=["speech"])
app.include_router(tutor.router, prefix="/api/v1/tutor", tags=["tutor"])

WEB_ROOT = Path(__file__).resolve().parents[4] / "apps" / "web"


@app.get("/")
async def root():
    return FileResponse(WEB_ROOT / "index.html")


def _database_ready() -> bool:
    try:
        with session_scope() as session:
            session.execute(db_text("SELECT 1"))
        return True
    except Exception:
        logger.exception("Database health check failed")
        return False


def _curriculum_ready() -> bool:
    return (Path(CURRICULUM_ROOT) / "registry.yaml").exists()


@app.get("/health")
def health():
    """Liveness-style status. Never provisions models or downloads anything."""
    db_ok = _database_ready()
    return {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "llm_available": is_llm_available(),
        "stt_available": is_stt_available(),
        "tts_available": is_tts_available(),
        "curriculum_loaded": _curriculum_ready(),
    }


@app.get("/readyz")
def readyz():
    """Readiness for orchestrators: the API can serve without an LLM, but not
    without a working database and curriculum registry."""
    db_ok = _database_ready()
    curriculum_ok = _curriculum_ready()
    ready = db_ok and curriculum_ok
    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "ready": ready,
            "db_connected": db_ok,
            "curriculum_loaded": curriculum_ok,
            "llm_available": is_llm_available(),
        },
    )
