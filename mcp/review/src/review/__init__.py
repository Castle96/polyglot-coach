"""
Polyglot Coach — Review MCP Service.

Schedules spaced repetition activities and records learner review outcomes
for long-term retention.
"""

from datetime import datetime, timedelta, timezone

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import ReviewItem


def get_due_words(profile_id: int, limit: int = 20) -> list[dict]:
    session = get_session()
    now = datetime.now(timezone.utc)
    items = (
        session.query(ReviewItem)
        .filter(ReviewItem.profile_id == profile_id, ReviewItem.next_review_at <= now)
        .order_by(ReviewItem.next_review_at.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": item.id,
            "word": item.word,
            "language": item.language,
            "interval": item.interval,
            "ease_factor": item.ease_factor,
            "repetitions": item.repetitions,
            "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
        }
        for item in items
    ]


def schedule_review(profile_id: int, word: str, language: str) -> dict:
    session = get_session()
    existing = (
        session.query(ReviewItem)
        .filter(
            ReviewItem.profile_id == profile_id,
            ReviewItem.word == word,
            ReviewItem.language == language,
        )
        .first()
    )
    if existing:
        return {
            "id": existing.id,
            "word": existing.word,
            "language": existing.language,
            "interval": existing.interval,
            "status": "already_scheduled",
            "next_review_at": existing.next_review_at.isoformat() if existing.next_review_at else None,
        }
    now = datetime.now(timezone.utc)
    item = ReviewItem(
        profile_id=profile_id,
        word=word,
        language=language,
        interval=1,
        ease_factor=2.5,
        repetitions=0,
        next_review_at=now,
    )
    session.add(item)
    session.commit()
    return {
        "id": item.id,
        "word": item.word,
        "language": item.language,
        "interval": item.interval,
        "status": "scheduled",
        "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
    }


def record_review(item_id: int, quality: int) -> dict:
    session = get_session()
    item = session.query(ReviewItem).filter(ReviewItem.id == item_id).first()
    if item is None:
        return {"error": f"Review item {item_id} not found"}
    quality = max(0, min(5, quality))
    if quality >= 3:
        item.repetitions += 1
        if item.repetitions == 1:
            item.interval = 1
        elif item.repetitions == 2:
            item.interval = 6
        else:
            item.interval = int(round(item.interval * item.ease_factor))
    else:
        item.repetitions = 0
        item.interval = 1
    item.ease_factor = max(1.3, item.ease_factor + 0.1 - (5 - quality) * 0.08)
    item.last_reviewed_at = datetime.now(timezone.utc)
    item.next_review_at = datetime.now(timezone.utc) + timedelta(days=item.interval)
    session.commit()
    return {
        "id": item.id,
        "word": item.word,
        "interval": item.interval,
        "ease_factor": item.ease_factor,
        "repetitions": item.repetitions,
        "next_review_at": item.next_review_at.isoformat() if item.next_review_at else None,
    }
