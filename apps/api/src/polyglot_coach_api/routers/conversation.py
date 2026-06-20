from fastapi import APIRouter

from conversation import evaluate_response, generate_scenario, suggest_followup

router = APIRouter()


@router.get("/scenarios")
def api_generate_scenario(language: str, level: str, topic: str | None = None):
    return generate_scenario(language=language, level=level, topic=topic)


@router.post("/evaluate")
def api_evaluate_response(scenario_id: int, user_turn: str):
    return evaluate_response(scenario_id=scenario_id, user_turn=user_turn)


@router.post("/followup")
def api_suggest_followup(scenario_id: int, conversation_history: list[str]):
    return suggest_followup(scenario_id=scenario_id, conversation_history=conversation_history)
