from fastapi import APIRouter, HTTPException

from grammar import explain_rule, generate_exercise, grade_exercise, lookup_rule
from polyglot_coach_api.validation import resolve_language_request
from polyglot_coach_shared.languages import get_language

router = APIRouter()


def _require_language(language: str) -> None:
    if get_language(language) is None:
        raise HTTPException(422, f"Unsupported language '{language}'")


@router.get("/rules/{rule_id}")
def api_lookup_rule(rule_id: str, language: str):
    _require_language(language)
    result = lookup_rule(rule_id=rule_id, language=language)
    if result is None:
        raise HTTPException(404, "Grammar rule not found")
    return result


@router.get("/explain")
def api_explain_rule(language: str, category: str, level: str | None = None):
    _, resolved_level, _ = resolve_language_request(language, level=level)
    return explain_rule(language=language, category=category, level=resolved_level)


@router.get("/exercises")
def api_generate_exercise(language: str, rule_id: str, count: int = 3):
    _require_language(language)
    return generate_exercise(language=language, rule_id=rule_id, count=count)


@router.post("/grade")
def api_grade_exercise(rule_id: str, language: str, user_answer: str):
    _require_language(language)
    return grade_exercise(rule_id=rule_id, language=language, user_answer=user_answer)
