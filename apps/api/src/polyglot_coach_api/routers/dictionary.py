from fastapi import APIRouter, HTTPException

from dictionary import get_conjugation, get_examples, lookup_word
from polyglot_coach_shared.languages import get_language

router = APIRouter()


def _require_language(language: str) -> None:
    if get_language(language) is None:
        raise HTTPException(422, f"Unsupported language '{language}'")


@router.get("/lookup")
def api_lookup_word(word: str, language: str, profile_id: int | None = None):
    _require_language(language)
    return lookup_word(word=word, language=language, profile_id=profile_id)


@router.get("/examples")
def api_get_examples(word: str, language: str, limit: int = 5):
    _require_language(language)
    return get_examples(word=word, language=language, limit=limit)


@router.get("/conjugation")
def api_get_conjugation(word: str, language: str):
    _require_language(language)
    return get_conjugation(word=word, language=language)
