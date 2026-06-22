from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from polyglot_coach_api.services.llm import TutorResult, generate_tutor_response, is_llm_available
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import VocabularyEntry

router = APIRouter()


class ChatRequest(BaseModel):
    profile_id: int
    message: str
    language: str
    level: str = "A1"
    mode: str = "conversation"
    locale: str = "neutral"
    conversation_history: list[dict] | None = None


class CorrectionItem(BaseModel):
    correction: str = ""
    why: str = ""
    alternative: str = ""


class ChatResponse(BaseModel):
    reply: str
    corrections: list[CorrectionItem] | None = None


@router.post("/chat", response_model=ChatResponse)
async def api_tutor_chat(body: ChatRequest):
    if not is_llm_available():
        raise HTTPException(503, "LLM model not loaded. Set POLYGLOT_LLM_MODEL_PATH and restart.")

    result: TutorResult = generate_tutor_response(
        message=body.message,
        language=body.language,
        level=body.level,
        history=body.conversation_history or [],
        profile_id=body.profile_id,
        mode=body.mode,
        locale=body.locale,
    )
    corrections = [
        CorrectionItem(correction=c.correction, why=c.why, alternative=c.alternative)
        for c in result.corrections
    ] if result.corrections else None

    return ChatResponse(reply=result.reply, corrections=corrections)


@router.get("/quick-chat", response_model=ChatResponse)
async def api_quick_chat(
    message: str = Query(..., description="User's message"),
    language: str = Query(..., description="Target language code (es, fr, de)"),
    level: str = Query("A1", description="CEFR level"),
    mode: str = Query("conversation", description="Learning mode (conversation, lesson, grammar, vocabulary, roleplay, assessment, immersion)"),
    locale: str = Query("neutral", description="Locale code (e.g. es_MX, fr_CA)"),
):
    """Lightweight chat endpoint for constrained devices (ESP32-C3 etc).

    Uses GET with query params — no JSON body needed.
    Falls back to curriculum-based responses when LLM is unavailable.
    """
    if is_llm_available():
        result: TutorResult = generate_tutor_response(
            message=message,
            language=language,
            level=level,
            history=[],
            mode=mode,
            locale=locale,
        )
        corrections = [
            CorrectionItem(correction=c.correction, why=c.why, alternative=c.alternative)
            for c in result.corrections
        ] if result.corrections else None
        return ChatResponse(reply=result.reply, corrections=corrections)

    session = get_session()
    total = session.query(func.count(VocabularyEntry.id)).filter(
        VocabularyEntry.language == language,
    ).scalar()
    corrections = None
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
