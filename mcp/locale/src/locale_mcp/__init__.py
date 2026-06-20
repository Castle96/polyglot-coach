"""
Polyglot Coach — Locale MCP Service.

Handles dialect-specific vocabulary, regional expressions, and pronunciation
preferences for supported locales.
"""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LocaleOverride


def get_locale(locale: str, language: str) -> dict:
    session = get_session()
    overrides = (
        session.query(LocaleOverride)
        .filter(LocaleOverride.locale == locale, LocaleOverride.language == language)
        .all()
    )
    return {
        "locale": locale,
        "language": language,
        "overrides_count": len(overrides),
        "overrides": [
            {
                "standard_word": o.standard_word,
                "local_word": o.local_word,
                "notes": o.notes,
            }
            for o in overrides
        ],
    }


def vocabulary_overrides(locale: str, language: str, words: list[str] | None = None) -> list[dict]:
    session = get_session()
    query = session.query(LocaleOverride).filter(
        LocaleOverride.locale == locale, LocaleOverride.language == language
    )
    if words:
        query = query.filter(LocaleOverride.standard_word.in_(words))
    overrides = query.all()
    return [
        {
            "standard_word": o.standard_word,
            "local_word": o.local_word,
            "notes": o.notes,
        }
        for o in overrides
    ]


def pronunciation_profile(locale: str, language: str) -> dict:
    known_profiles = {
        "es_ES": {"name": "Castilian Spanish", "features": ["distinción", "ceceo", "vosotros"]},
        "es_MX": {"name": "Mexican Spanish", "features": ["seseo", "ustedes", "diminutives"]},
        "fr_FR": {"name": "Metropolitan French", "features": ["neutral r", "liaison"]},
        "fr_CA": {"name": "Quebec French", "features": ["affrication", "diphtongization"]},
    }
    profile = known_profiles.get(locale)
    if profile is None:
        return {
            "locale": locale,
            "language": language,
            "message": f"Pronunciation profile for '{locale}' is not yet defined.",
        }
    return {"locale": locale, "language": language, **profile}
