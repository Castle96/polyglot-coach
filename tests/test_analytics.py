"""Tests for the analytics MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import MistakeRecord, ProgressRecord, ReviewItem, VocabularyEntry


def _seed_data():
    session = get_session(":memory:")
    session.add_all([
        VocabularyEntry(profile_id=0, word="hola", translation="hello", language="es"),
        VocabularyEntry(profile_id=0, word="adios", translation="goodbye", language="es"),
        VocabularyEntry(profile_id=0, word="gracias", translation="thank you", language="es"),
        ProgressRecord(profile_id=0, event_type="lesson", detail="Lesson 1"),
        ProgressRecord(profile_id=0, event_type="lesson", detail="Lesson 2"),
        MistakeRecord(profile_id=0, category="grammar", user_input="bad", correction="good"),
        MistakeRecord(profile_id=0, category="vocabulary", user_input="wrong", correction="right"),
        ReviewItem(profile_id=0, word="hola", language="es", interval=1, ease_factor=2.5, repetitions=3),
        ReviewItem(profile_id=0, word="adios", language="es", interval=5, ease_factor=2.5, repetitions=1),
        ReviewItem(profile_id=0, word="gracias", language="es", interval=1, ease_factor=2.5, repetitions=0),
    ])
    session.commit()
    session.close()


def test_get_learning_summary():
    from analytics import get_learning_summary

    _seed_data()
    summary = get_learning_summary(profile_id=0)
    assert summary["vocabulary_learned"] == 3
    assert summary["mistakes_recorded"] == 2
    assert summary["events_last_7_days"] >= 2


def test_get_learning_summary_empty():
    from analytics import get_learning_summary

    summary = get_learning_summary(profile_id=999)
    assert summary["vocabulary_learned"] == 0
    assert summary["mistakes_recorded"] == 0


def test_get_retention_report():
    from analytics import get_retention_report

    _seed_data()
    report = get_retention_report(profile_id=0)
    assert report["total_words_tracked"] == 3
    assert report["mastered"] == 1
    assert report["learning"] == 1
    assert report["new"] == 1


def test_get_retention_report_empty():
    from analytics import get_retention_report

    report = get_retention_report(profile_id=999)
    assert report["total_words_tracked"] == 0


def test_get_engagement_overview():
    from analytics import get_engagement_overview

    _seed_data()
    overview = get_engagement_overview(profile_id=0)
    assert overview["total_mistakes_last_30_days"] == 2
    assert "grammar" in overview["mistakes_by_category"]
    assert overview["mistakes_by_category"]["vocabulary"] == 1
