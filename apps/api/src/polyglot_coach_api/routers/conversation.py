from fastapi import APIRouter

from conversation import evaluate_response, generate_scenario, suggest_followup
from polyglot_coach_api.validation import resolve_language_request

router = APIRouter()


@router.get("/scenarios")
def api_generate_scenario(language: str, level: str | None = None, topic: str | None = None):
    _, resolved_level, _ = resolve_language_request(language, level=level)
    return generate_scenario(language=language, level=resolved_level, topic=topic)


@router.post("/evaluate")
def api_evaluate_response(scenario_id: int, user_turn: str):
    return evaluate_response(scenario_id=scenario_id, user_turn=user_turn)


@router.post("/followup")
def api_suggest_followup(scenario_id: int, conversation_history: list[str]):
    return suggest_followup(scenario_id=scenario_id, conversation_history=conversation_history)
