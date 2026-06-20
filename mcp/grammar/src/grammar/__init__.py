"""
Polyglot Coach — Grammar MCP Service.

Explains grammar rules, generates exercises, and evaluates learner responses
in context.
"""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import GrammarRule


def lookup_rule(rule_id: str, language: str) -> dict | None:
    session = get_session()
    rule = (
        session.query(GrammarRule)
        .filter(GrammarRule.rule_id == rule_id, GrammarRule.language == language)
        .first()
    )
    if rule is None:
        return None
    return {
        "id": rule.id,
        "rule_id": rule.rule_id,
        "title": rule.title,
        "explanation": rule.explanation,
        "examples": rule.examples,
        "level": rule.level,
        "category": rule.category,
    }


def explain_rule(language: str, category: str, level: str) -> list[dict]:
    session = get_session()
    rules = (
        session.query(GrammarRule)
        .filter(GrammarRule.language == language, GrammarRule.category == category, GrammarRule.level == level)
        .all()
    )
    return [
        {
            "rule_id": r.rule_id,
            "title": r.title,
            "explanation": r.explanation,
            "examples": r.examples,
        }
        for r in rules
    ]


def generate_exercise(language: str, rule_id: str, count: int = 3) -> dict:
    session = get_session()
    rule = (
        session.query(GrammarRule)
        .filter(GrammarRule.rule_id == rule_id, GrammarRule.language == language)
        .first()
    )
    if rule is None:
        return {"error": f"Rule '{rule_id}' not found for {language}"}
    return {
        "rule": rule.title,
        "level": rule.level,
        "category": rule.category,
        "prompt": f"Create {count} practice exercises for: {rule.title}",
        "hint": rule.explanation[:200] if rule.explanation else None,
    }


def grade_exercise(rule_id: str, language: str, user_answer: str) -> dict:
    session = get_session()
    rule = (
        session.query(GrammarRule)
        .filter(GrammarRule.rule_id == rule_id, GrammarRule.language == language)
        .first()
    )
    return {
        "rule_id": rule_id,
        "language": language,
        "user_answer": user_answer,
        "expected_patterns": rule.examples.split("\n") if rule and rule.examples else [],
        "status": "received",
    }
