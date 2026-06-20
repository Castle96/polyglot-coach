from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from polyglot_coach_api.services.llm import generate_tutor_response, is_llm_available
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import VocabularyEntry

router = APIRouter()


class ChatRequest(BaseModel):
    profile_id: int
    message: str
    language: str
    level: str = "A1"
    conversation_history: list[dict] | None = None


class ChatResponse(BaseModel):
    reply: str
    corrections: list[str] | None = None


@router.post("/chat", response_model=ChatResponse)
async def api_tutor_chat(body: ChatRequest):
    if not is_llm_available():
        raise HTTPException(503, "LLM model not loaded. Set POLYGLOT_LLM_MODEL_PATH and restart.")

    reply = generate_tutor_response(
        message=body.message,
        language=body.language,
        level=body.level,
        history=body.conversation_history or [],
    )
    return ChatResponse(reply=reply, corrections=None)


@router.get("/quick-chat", response_model=ChatResponse)
async def api_quick_chat(
    message: str = Query(..., description="User's message"),
    language: str = Query(..., description="Target language code (es, fr, de)"),
    level: str = Query("A1", description="CEFR level"),
):
    """Lightweight chat endpoint for constrained devices (ESP32-C3 etc).

    Uses GET with query params — no JSON body needed.
    Falls back to curriculum-based responses when LLM is unavailable.
    """
    if is_llm_available():
        reply = generate_tutor_response(message=message, language=language, level=level, history=[])
        return ChatResponse(reply=reply, corrections=None)

    session = get_session()
    total = session.query(func.count(VocabularyEntry.id)).filter(
        VocabularyEntry.language == language,
    ).scalar()
    corrections = []
    reply = ""
    if total:
        word = session.query(VocabularyEntry).filter(
            VocabularyEntry.language == language,
        ).order_by(func.random()).first()
        reply = (
            f"Let's practice! Try using the word \"{word.word}\" "
            f"(meaning: {word.translation}) in a sentence.\n\n"
            f"Your message: \"{message}\"\n\n"
            f"Keep practicing — every word counts!"
        )
    else:
        reply = (
            f"I hear you! Unfortunately I don't have curriculum data loaded for {language} yet. "
            f"Try: es (Spanish), fr (French), or de (German).\n\n"
            f"You said: \"{message}\""
        )
    session.close()
    return ChatResponse(reply=reply, corrections=corrections)


@router.get("/status")
async def api_tutor_status():
    return {"llm_available": is_llm_available()}
