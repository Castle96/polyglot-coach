from fastapi import APIRouter

from dictionary import get_conjugation, get_examples, lookup_word

router = APIRouter()


@router.get("/lookup")
def api_lookup_word(word: str, language: str, profile_id: int | None = None):
    return lookup_word(word=word, language=language, profile_id=profile_id)


@router.get("/examples")
def api_get_examples(word: str, language: str, limit: int = 5):
    return get_examples(word=word, language=language, limit=limit)


@router.get("/conjugation")
def api_get_conjugation(word: str, language: str):
    return get_conjugation(word=word, language=language)
