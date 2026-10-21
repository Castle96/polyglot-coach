from fastapi import APIRouter, HTTPException

from curriculum import get_lesson, get_scenario, get_topic
from polyglot_coach_api.validation import resolve_language_request
from polyglot_coach_shared.languages import get_language

router = APIRouter()


@router.get("/lessons")
def api_get_lesson(language: str, level: str | None = None):
    _, resolved_level, _ = resolve_language_request(language, level=level)
    return get_lesson(language=language, level=resolved_level)


@router.get("/topics")
def api_get_topic(language: str, level: str | None = None):
    if get_language(language) is None:
        raise HTTPException(422, f"Unsupported language '{language}'")
    if level is not None:
        _, level, _ = resolve_language_request(language, level=level)
    return get_topic(language=language, level=level)


@router.get("/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: int):
    result = get_scenario(scenario_id=scenario_id)
    if result is None:
        raise HTTPException(404, "Scenario not found")
    return result
