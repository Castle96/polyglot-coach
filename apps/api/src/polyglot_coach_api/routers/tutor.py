from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func

from polyglot_coach_api.services.llm import TutorResult, generate_tutor_response, is_llm_available
from polyglot_coach_api.validation import resolve_language_request
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.languages import features_for, list_public_languages, resolve_selection
from polyglot_coach_shared.models import VocabularyEntry

router = APIRouter()


class ChatRequest(BaseModel):
    profile_id: int
    message: str
    language: str
    level: str | None = None
    mode: str = "conversation"
    locale: str | None = None
    features: list[str] | None = None
    conversation_history: list[dict] | None = None


class CorrectionItem(BaseModel):
    correction: str = ""
    why: str = ""
    alternative: str = ""


class ChatResponse(BaseModel):
    reply: str
    corrections: list[CorrectionItem] | None = None
    language: str | None = None
    level: str | None = None
    locale: str | None = None
    features: list[str] | None = None


def _feature_names(language: str, level: str, feature_ids: list[str] | None) -> list[str]:
    if not feature_ids:
        return []
    names = {feature["id"]: feature["name"] for feature in features_for(language, level)}
    return [names.get(feature_id, feature_id) for feature_id in feature_ids]


@router.post("/chat", response_model=ChatResponse)
async def api_tutor_chat(body: ChatRequest):
    _, level, locale = resolve_language_request(
        body.language,
        level=body.level,
        locale=body.locale,
        features=body.features,
    )
    if not is_llm_available():
        raise HTTPException(503, "LLM model not loaded. Set POLYGLOT_LLM_MODEL_PATH and restart.")

    result: TutorResult = generate_tutor_response(
        message=body.message,
        language=body.language,
        level=level,
        history=body.conversation_history or [],
        profile_id=body.profile_id,
        mode=body.mode,
        locale=locale,
        feature_focus=body.features,
    )
    corrections = [
        CorrectionItem(correction=c.correction, why=c.why, alternative=c.alternative)
        for c in result.corrections
    ] if result.corrections else None

    return ChatResponse(
        reply=result.reply,
        corrections=corrections,
        language=body.language,
        level=level,
        locale=locale,
        features=body.features,
    )


@router.get("/quick-chat", response_model=ChatResponse)
async def api_quick_chat(
    message: str = Query(..., description="User's message"),
    language: str = Query(..., description="Target language code (ISO 639-1)"),
    level: str | None = Query(None, description="Level within the target language's framework"),
    mode: str = Query("conversation", description="Learning mode (conversation, lesson, grammar, vocabulary, roleplay, assessment, immersion)"),
    locale: str | None = Query(None, description="Locale code (e.g. es_MX, fr_CA)"),
    features: str | None = Query(None, description="Comma-separated language feature ids"),
):
    """Lightweight chat endpoint for constrained devices (ESP32-C3 etc).

    Uses GET with query params — no JSON body needed.
    Falls back to curriculum-based responses when LLM is unavailable.
    """
    feature_focus = [item.strip() for item in features.split(",") if item.strip()] if features else None
    pack, level, locale = resolve_language_request(
        language,
        level=level,
        locale=locale,
        features=feature_focus,
    )

    if is_llm_available():
        result: TutorResult = generate_tutor_response(
            message=message,
            language=language,
            level=level,
            history=[],
            mode=mode,
            locale=locale,
            feature_focus=feature_focus,
        )
        corrections = [
            CorrectionItem(correction=c.correction, why=c.why, alternative=c.alternative)
            for c in result.corrections
        ] if result.corrections else None
        return ChatResponse(
            reply=result.reply,
            corrections=corrections,
            language=language,
            level=level,
            locale=locale,
            features=feature_focus,
        )

    session = get_session()
    total = session.query(func.count(VocabularyEntry.id)).filter(
        VocabularyEntry.language == language,
    ).scalar()
    reply = ""
    if total:
        word = session.query(VocabularyEntry).filter(
            VocabularyEntry.language == language,
        ).order_by(func.random()).first()
        reply = (
            f"Let's practice {pack.get('name', language)}! Try using the word \"{word.word}\" "
            f"(meaning: {word.translation}) in a sentence.\n\n"
            f"Your message: \"{message}\"\n\n"
            f"Keep practicing — every word counts!"
        )
    else:
        available = ", ".join(item["code"] for item in list_public_languages())
        reply = (
            f"I hear you! Unfortunately I don't have curriculum data loaded for {language} yet. "
            f"Try: {available}.\n\n"
            f"You said: \"{message}\""
        )
    session.close()

    focus_names = _feature_names(language, level, feature_focus)
    if focus_names:
        reply += f"\n\nFocus: {', '.join(focus_names)}."
    return ChatResponse(
        reply=reply,
        corrections=None,
        language=language,
        level=level,
        locale=locale,
        features=feature_focus,
    )


@router.get("/status")
def api_tutor_status():
    return {"llm_available": is_llm_available()}


@router.get("/options")
def api_tutor_options(language: str, level: str | None = None):
    """Return the resolved level and available features for a target language."""
    try:
        pack, resolved_level, _ = resolve_selection(language, level=level)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "language": pack.get("code"),
        "level": resolved_level,
        "features": features_for(language, resolved_level),
    }
