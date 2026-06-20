"""Tests for the review MCP service."""




def test_get_due_words_empty():
    from review import get_due_words

    assert get_due_words(profile_id=0) == []


def test_schedule_review():
    from review import schedule_review

    result = schedule_review(profile_id=0, word="bonjour", language="fr")
    assert result["word"] == "bonjour"
    assert result["status"] == "scheduled"


def test_schedule_review_duplicate():
    from review import schedule_review

    schedule_review(profile_id=0, word="bonjour", language="fr")
    result = schedule_review(profile_id=0, word="bonjour", language="fr")
    assert result["status"] == "already_scheduled"


def test_get_due_words_after_scheduling():
    from review import get_due_words, schedule_review

    schedule_review(profile_id=0, word="hola", language="es")
    due = get_due_words(profile_id=0)
    assert len(due) >= 1
    assert due[0]["word"] == "hola"


def test_record_review():
    from review import record_review, schedule_review

    scheduled = schedule_review(profile_id=0, word="merci", language="fr")
    result = record_review(item_id=scheduled["id"], quality=4)
    assert result["repetitions"] == 1
    assert result["interval"] >= 1
    assert "next_review_at" in result


def test_record_review_not_found():
    from review import record_review

    result = record_review(item_id=999, quality=3)
    assert "error" in result


def test_record_review_poor_quality_resets():
    from review import record_review, schedule_review

    scheduled = schedule_review(profile_id=0, word="adieu", language="fr")
    record_review(item_id=scheduled["id"], quality=4)
    result = record_review(item_id=scheduled["id"], quality=1)
    assert result["repetitions"] == 0
    assert result["interval"] == 1
