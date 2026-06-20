from fastapi import APIRouter

from curriculum import get_lesson, get_scenario, get_topic

router = APIRouter()


@router.get("/lessons")
def api_get_lesson(language: str, level: str):
    return get_lesson(language=language, level=level)


@router.get("/topics")
def api_get_topic(language: str, level: str | None = None):
    return get_topic(language=language, level=level)


@router.get("/scenarios/{scenario_id}")
def api_get_scenario(scenario_id: int):
    result = get_scenario(scenario_id=scenario_id)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Scenario not found")
    return result
