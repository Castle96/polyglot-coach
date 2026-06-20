"""
Polyglot Coach — Dictionary MCP Service.

Provides definitions, example usage, conjugations, and vocabulary metadata
for supported teaching flows.
"""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import VocabularyEntry


def lookup_word(word: str, language: str, profile_id: int | None = None) -> dict:
    session = get_session()
    query = session.query(VocabularyEntry).filter(
        VocabularyEntry.word == word, VocabularyEntry.language == language
    )
    if profile_id is not None:
        query = query.filter(VocabularyEntry.profile_id == profile_id)
    entries = query.all()
    return {
        "word": word,
        "language": language,
        "entries": [
            {
                "id": e.id,
                "translation": e.translation,
                "context_sentence": e.context_sentence,
                "tags": e.tags.split(",") if e.tags else [],
            }
            for e in entries
        ],
    }


def get_examples(word: str, language: str, limit: int = 5) -> list[dict]:
    session = get_session()
    entries = (
        session.query(VocabularyEntry)
        .filter(VocabularyEntry.word == word, VocabularyEntry.language == language)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "word": e.word,
            "translation": e.translation,
            "context_sentence": e.context_sentence,
        }
        for e in entries
        if e.context_sentence
    ]


def get_conjugation(word: str, language: str) -> dict:
    return {
        "word": word,
        "language": language,
        "message": f"Conjugation data for '{word}' ({language}) will be available with model-powered lookup.",
    }
