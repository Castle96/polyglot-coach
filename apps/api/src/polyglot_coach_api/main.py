from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text as db_text

from pathlib import Path

from polyglot_coach_api.data.loader import CURRICULUM_ROOT, load_all_curriculum_data
from polyglot_coach_api.routers import analytics, conversation, curriculum, dictionary, grammar, learner, locale, review, tutor
from polyglot_coach_shared.database import get_session
from polyglot_coach_api.services.llm import is_llm_available


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_all_curriculum_data()
    yield


app = FastAPI(
    title="Polyglot Coach API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(learner.router, prefix="/api/v1/learner", tags=["learner"])
app.include_router(curriculum.router, prefix="/api/v1/curriculum", tags=["curriculum"])
app.include_router(dictionary.router, prefix="/api/v1/dictionary", tags=["dictionary"])
app.include_router(grammar.router, prefix="/api/v1/grammar", tags=["grammar"])
app.include_router(locale.router, prefix="/api/v1/locale", tags=["locale"])
app.include_router(conversation.router, prefix="/api/v1/conversation", tags=["conversation"])
app.include_router(review.router, prefix="/api/v1/review", tags=["review"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(tutor.router, prefix="/api/v1/tutor", tags=["tutor"])

WEB_ROOT = Path(__file__).resolve().parents[4] / "apps" / "web"


@app.get("/")
async def root():
    return FileResponse(WEB_ROOT / "index.html")


@app.get("/health")
async def health():
    db_ok = False
    try:
        session = get_session()
        session.execute(db_text("SELECT 1"))
        session.close()
        db_ok = True
    except Exception:
        pass
    llm_ok = is_llm_available()
    return {
        "status": "ok" if db_ok else "degraded",
        "db_connected": db_ok,
        "llm_available": llm_ok,
        "curriculum_loaded": Path(CURRICULUM_ROOT).exists(),
    }
