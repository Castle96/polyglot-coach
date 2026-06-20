"""Tests for the learner-memory MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LearnerProfile, ProgressRecord


def _create_profile(name="Alice", target="es", level="A1") -> int:
    session = get_session(":memory:")
    p = LearnerProfile(name=name, native_language="en", target_language=target, locale="es_MX", proficiency_level=level)
    session.add(p)
    session.commit()
    profile_id = p.id
    session.close()
    return profile_id


def test_get_profile_returns_none_for_missing():
    from learner_memory import get_profile

    assert get_profile("nonexistent") is None


def test_get_profile_found():
    from learner_memory import get_profile

    _create_profile("Alice", target="fr", level="A2")
    found = get_profile("Alice")
    assert found is not None
    assert found["name"] == "Alice"
    assert found["target_language"] == "fr"
    assert found["proficiency_level"] == "A2"


def test_update_profile_partial():
    from learner_memory import update_profile

    pid = _create_profile("Bob", level="A1")
    result = update_profile(profile_id=pid, proficiency_level="B1")
    assert result["proficiency_level"] == "B1"


def test_update_profile_missing_id():
    from learner_memory import update_profile

    assert update_profile(profile_id=999) is None


def test_record_mistake():
    from learner_memory import record_mistake

    mistake = record_mistake(
        profile_id=0,
        category="grammar",
        user_input="Yo es cansado",
        correction="Yo estoy cansado",
    )
    assert mistake["category"] == "grammar"
    assert mistake["user_input"] == "Yo es cansado"
    assert "id" in mistake


def test_get_progress_empty():
    from learner_memory import get_progress

    assert get_progress(profile_id=0) == []


def test_get_progress_with_records():
    from learner_memory import get_progress

    session = get_session(":memory:")
    session.add(ProgressRecord(profile_id=0, event_type="test_event", detail="test detail", score=90.0))
    session.commit()
    session.close()

    records = get_progress(profile_id=0)
    assert len(records) >= 1
    assert records[0]["event_type"] == "test_event"
    assert records[0]["score"] == 90.0


def test_get_progress_filtered():
    from learner_memory import get_progress

    records = get_progress(profile_id=0, event_type="nonexistent")
    assert records == []
