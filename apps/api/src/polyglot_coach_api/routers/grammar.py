from fastapi import APIRouter

from grammar import explain_rule, generate_exercise, grade_exercise, lookup_rule

router = APIRouter()


@router.get("/rules/{rule_id}")
def api_lookup_rule(rule_id: str, language: str):
    result = lookup_rule(rule_id=rule_id, language=language)
    if result is None:
        from fastapi import HTTPException
        raise HTTPException(404, "Grammar rule not found")
    return result


@router.get("/explain")
def api_explain_rule(language: str, category: str, level: str):
    return explain_rule(language=language, category=category, level=level)


@router.get("/exercises")
def api_generate_exercise(language: str, rule_id: str, count: int = 3):
    return generate_exercise(language=language, rule_id=rule_id, count=count)


@router.post("/grade")
def api_grade_exercise(rule_id: str, language: str, user_answer: str):
    return grade_exercise(rule_id=rule_id, language=language, user_answer=user_answer)
