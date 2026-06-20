"""Tests for the dictionary MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import VocabularyEntry


def _seed_vocabulary():
    session = get_session(":memory:")
    session.add_all([
        VocabularyEntry(profile_id=0, word="bonjour", translation="hello", language="fr", context_sentence="Bonjour, comment ça va?", tags="greeting"),
        VocabularyEntry(profile_id=0, word="merci", translation="thank you", language="fr", context_sentence="Merci beaucoup!", tags="courtesy"),
        VocabularyEntry(profile_id=0, word="hola", translation="hello", language="es", context_sentence="Hola, ¿cómo estás?", tags="greeting"),
    ])
    session.commit()
    session.close()


def test_lookup_word():
    from dictionary import lookup_word

    _seed_vocabulary()
    result = lookup_word(word="bonjour", language="fr")
    assert result["word"] == "bonjour"
    assert len(result["entries"]) >= 1
    assert result["entries"][0]["translation"] == "hello"


def test_lookup_word_empty():
    from dictionary import lookup_word

    result = lookup_word(word="xyzzy", language="fr")
    assert len(result["entries"]) == 0


def test_get_examples():
    from dictionary import get_examples

    _seed_vocabulary()
    examples = get_examples(word="bonjour", language="fr")
    assert len(examples) >= 1
    assert examples[0]["context_sentence"] == "Bonjour, comment ça va?"


def test_get_examples_no_results():
    from dictionary import get_examples

    assert get_examples(word="xyzzy", language="fr") == []


def test_get_conjugation():
    from dictionary import get_conjugation

    result = get_conjugation(word="hablar", language="es")
    assert result["word"] == "hablar"
    assert result["language"] == "es"
