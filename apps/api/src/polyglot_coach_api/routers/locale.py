from fastapi import APIRouter

from locale_mcp import get_locale, pronunciation_profile, vocabulary_overrides

router = APIRouter()


@router.get("/{locale}")
def api_get_locale(locale: str, language: str):
    return get_locale(locale=locale, language=language)


@router.get("/{locale}/overrides")
def api_vocabulary_overrides(locale: str, language: str, words: str | None = None):
    word_list = words.split(",") if words else None
    return vocabulary_overrides(locale=locale, language=language, words=word_list)


@router.get("/{locale}/pronunciation")
def api_pronunciation_profile(locale: str, language: str):
    return pronunciation_profile(locale=locale, language=language)
