"""
Polyglot Coach — Learner Memory MCP Service.

Stores and retrieves learner progress including vocabulary tracking,
grammar tracking, mistake tracking, and progress summaries.
"""

import difflib
from datetime import datetime, timezone

from polyglot_coach_shared import MistakeRecord, ProgressRecord
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LearnerProfile, Session


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


def save_session(
    profile_id: int,
    title: str,
    language: str,
    state: str,
    session_id: int | None = None,
) -> dict:
    db_session = get_session()
    if session_id:
        session_obj = db_session.query(Session).filter(Session.id == session_id).first()
        if session_obj:
            session_obj.title = title
            session_obj.language = language
            session_obj.state = state
            session_obj.updated_at = datetime.now(timezone.utc)
        else:
            return None
    else:
        session_obj = Session(
            profile_id=profile_id,
            title=title,
            language=language,
            state=state,
        )
        db_session.add(session_obj)
    db_session.commit()
    return {
        "id": session_obj.id,
        "profile_id": session_obj.profile_id,
        "title": session_obj.title,
        "language": session_obj.language,
        "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
        "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else None,
    }


def list_sessions(
    profile_id: int,
    language: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> list[dict]:
    db_session = get_session()
    q = db_session.query(Session).filter(Session.profile_id == profile_id)
    if language:
        q = q.filter(Session.language == language)
    sessions = q.order_by(Session.updated_at.desc()).limit(limit).all()

    if query:
        titles = [(s, s.title.lower()) for s in sessions]
        matches = difflib.get_close_matches(query.lower(), [t for _, t in titles], n=limit, cutoff=0.6)
        sessions = [s for s, t in titles if t in matches or any(m in t for m in query.lower().split())]

    return [
        {
            "id": s.id,
            "profile_id": s.profile_id,
            "title": s.title,
            "language": s.language,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in sessions
    ]


def load_session(session_id: int) -> dict | None:
    db_session = get_session()
    session_obj = db_session.query(Session).filter(Session.id == session_id).first()
    if session_obj is None:
        return None
    return {
        "id": session_obj.id,
        "profile_id": session_obj.profile_id,
        "title": session_obj.title,
        "language": session_obj.language,
        "state": session_obj.state,
        "created_at": session_obj.created_at.isoformat() if session_obj.created_at else None,
        "updated_at": session_obj.updated_at.isoformat() if session_obj.updated_at else None,
    }


def delete_session(session_id: int) -> bool:
    db_session = get_session()
    session_obj = db_session.query(Session).filter(Session.id == session_id).first()
    if session_obj is None:
        return False
    db_session.delete(session_obj)
    db_session.commit()
    return True


def export_vocabulary_json(profile_id: int) -> list[dict]:
    from polyglot_coach_shared.models import VocabularyEntry
    db_session = get_session()
    entries = db_session.query(VocabularyEntry).filter(VocabularyEntry.profile_id == profile_id).all()
    return [
        {
            "word": e.word,
            "translation": e.translation,
            "language": e.language,
            "context_sentence": e.context_sentence,
            "tags": e.tags,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]


def export_vocabulary_csv(profile_id: int) -> str:
    from polyglot_coach_shared.models import VocabularyEntry
    db_session = get_session()
    entries = db_session.query(VocabularyEntry).filter(VocabularyEntry.profile_id == profile_id).all()
    lines = ["word,translation,language,context,tags"]
    for e in entries:
        context = (e.context_sentence or "").replace(",", ";").replace("\n", " ")
        tags = e.tags or ""
        lines.append(f'"{e.word}","{e.translation}","{e.language}","{context}","{tags}"')
    return "\n".join(lines)


def export_anki_deck(profile_id: int, language: str | None = None) -> str:
    from polyglot_coach_shared.models import VocabularyEntry
    db_session = get_session()
    query = db_session.query(VocabularyEntry).filter(VocabularyEntry.profile_id == profile_id)
    if language:
        query = query.filter(VocabularyEntry.language == language)
    entries = query.all()

    cards = []
    for e in entries:
        front = e.word
        back = e.translation
        if e.context_sentence:
            back += f"<br><i>{e.context_sentence}</i>"
        cards.append(f"{front}\t{back}")

    return "\n".join(cards)
