"""
Polyglot Coach — Learner Memory MCP Service.

Stores and retrieves learner progress including vocabulary tracking,
grammar tracking, mistake tracking, and progress summaries.
"""

from datetime import datetime, timezone

from polyglot_coach_shared import MistakeRecord, ProgressRecord
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LearnerProfile


def get_profile(name: str) -> dict | None:
    session = get_session()
    profile = session.query(LearnerProfile).filter(LearnerProfile.name == name).first()
    if profile is None:
        return None
    return {
        "id": profile.id,
        "name": profile.name,
        "native_language": profile.native_language,
        "target_language": profile.target_language,
        "locale": profile.locale,
        "proficiency_level": profile.proficiency_level,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def update_profile(
    profile_id: int,
    name: str | None = None,
    native_language: str | None = None,
    target_language: str | None = None,
    locale: str | None = None,
    proficiency_level: str | None = None,
) -> dict | None:
    session = get_session()
    profile = session.query(LearnerProfile).filter(LearnerProfile.id == profile_id).first()
    if profile is None:
        return None
    if name is not None:
        profile.name = name
    if native_language is not None:
        profile.native_language = native_language
    if target_language is not None:
        profile.target_language = target_language
    if locale is not None:
        profile.locale = locale
    if proficiency_level is not None:
        profile.proficiency_level = proficiency_level
    profile.updated_at = datetime.now(timezone.utc)
    session.commit()
    return {
        "id": profile.id,
        "name": profile.name,
        "native_language": profile.native_language,
        "target_language": profile.target_language,
        "locale": profile.locale,
        "proficiency_level": profile.proficiency_level,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
    }


def record_mistake(
    profile_id: int,
    category: str,
    user_input: str,
    correction: str,
    explanation: str | None = None,
    context: str | None = None,
) -> dict:
    session = get_session()
    mistake = MistakeRecord(
        profile_id=profile_id,
        category=category,
        user_input=user_input,
        correction=correction,
        explanation=explanation,
        context=context,
    )
    session.add(mistake)
    session.commit()
    return {
        "id": mistake.id,
        "profile_id": mistake.profile_id,
        "category": mistake.category,
        "user_input": mistake.user_input,
        "correction": mistake.correction,
        "explanation": mistake.explanation,
        "context": mistake.context,
        "created_at": mistake.created_at.isoformat(),
    }


def get_progress(profile_id: int, event_type: str | None = None, limit: int = 50) -> list[dict]:
    session = get_session()
    query = session.query(ProgressRecord).filter(ProgressRecord.profile_id == profile_id)
    if event_type:
        query = query.filter(ProgressRecord.event_type == event_type)
    records = query.order_by(ProgressRecord.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "profile_id": r.profile_id,
            "event_type": r.event_type,
            "detail": r.detail,
            "score": r.score,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
