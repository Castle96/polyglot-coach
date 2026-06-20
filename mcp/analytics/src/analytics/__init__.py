"""
Polyglot Coach — Analytics MCP Service.

Aggregates learning activity and progress signals into analytics views and
summary reporting.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import MistakeRecord, ProgressRecord, ReviewItem, VocabularyEntry


def get_learning_summary(profile_id: int) -> dict:
    session = get_session()
    vocab_count = session.query(func.count(VocabularyEntry.id)).filter(VocabularyEntry.profile_id == profile_id).scalar()
    mistake_count = session.query(func.count(MistakeRecord.id)).filter(MistakeRecord.profile_id == profile_id).scalar()
    review_due = (
        session.query(func.count(ReviewItem.id))
        .filter(ReviewItem.profile_id == profile_id, ReviewItem.next_review_at <= datetime.now(timezone.utc))
        .scalar()
    )
    recent_progress = (
        session.query(ProgressRecord)
        .filter(ProgressRecord.profile_id == profile_id, ProgressRecord.created_at >= datetime.now(timezone.utc) - timedelta(days=7))
        .count()
    )
    return {
        "profile_id": profile_id,
        "vocabulary_learned": vocab_count or 0,
        "mistakes_recorded": mistake_count or 0,
        "words_due_for_review": review_due or 0,
        "events_last_7_days": recent_progress or 0,
    }


def get_retention_report(profile_id: int) -> dict:
    session = get_session()
    items = session.query(ReviewItem).filter(ReviewItem.profile_id == profile_id).all()
    if not items:
        return {"profile_id": profile_id, "total_words_tracked": 0, "average_ease_factor": 2.5}
    avg_ease = sum(i.ease_factor for i in items) / len(items)
    mastered = sum(1 for i in items if i.repetitions >= 3)
    learning = sum(1 for i in items if 0 < i.repetitions < 3)
    new_words = sum(1 for i in items if i.repetitions == 0)
    return {
        "profile_id": profile_id,
        "total_words_tracked": len(items),
        "average_ease_factor": round(avg_ease, 2),
        "mastered": mastered,
        "learning": learning,
        "new": new_words,
    }


def get_engagement_overview(profile_id: int) -> dict:
    session = get_session()
    now = datetime.now(timezone.utc)
    days_30 = now - timedelta(days=30)
    progress_events = (
        session.query(ProgressRecord)
        .filter(ProgressRecord.profile_id == profile_id, ProgressRecord.created_at >= days_30)
        .all()
    )
    mistakes_30 = (
        session.query(MistakeRecord)
        .filter(MistakeRecord.profile_id == profile_id, MistakeRecord.created_at >= days_30)
        .all()
    )
    categories: dict[str, int] = {}
    for m in mistakes_30:
        categories[m.category] = categories.get(m.category, 0) + 1
    return {
        "profile_id": profile_id,
        "total_sessions_last_30_days": len(progress_events),
        "total_mistakes_last_30_days": len(mistakes_30),
        "mistakes_by_category": categories,
        "current_streak_days": 0,
    }
