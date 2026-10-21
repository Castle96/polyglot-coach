"""Request validation against curriculum language packs."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from polyglot_coach_shared.languages import resolve_selection


def resolve_language_request(
    language: str,
    level: str | None = None,
    locale: str | None = None,
    features: list[str] | None = None,
) -> tuple[dict[str, Any], str, str]:
    """Validate a language selection or raise a 422 with a useful message."""
    try:
        return resolve_selection(language, level=level, locale=locale, features=features)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
