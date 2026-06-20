"""Tests for the grammar MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import GrammarRule


def _seed_rules():
    session = get_session(":memory:")
    session.add_all([
        GrammarRule(
            language="es",
            rule_id="es_verb_ser_estar",
            title="Ser vs Estar",
            explanation="Ser is for permanent states, estar for temporary.",
            examples="Soy alto.\nEstoy cansado.",
            level="A1",
            category="verbs",
        ),
        GrammarRule(
            language="es",
            rule_id="es_noun_gender",
            title="Noun Gender",
            explanation="Spanish nouns are masculine or feminine.",
            examples="El libro\nLa casa",
            level="A1",
            category="nouns",
        ),
    ])
    session.commit()
    session.close()


def test_lookup_rule_found():
    from grammar import lookup_rule

    _seed_rules()
    rule = lookup_rule(rule_id="es_verb_ser_estar", language="es")
    assert rule is not None
    assert rule["title"] == "Ser vs Estar"
    assert rule["level"] == "A1"


def test_lookup_rule_not_found():
    from grammar import lookup_rule

    assert lookup_rule(rule_id="nonexistent", language="es") is None


def test_explain_rule():
    from grammar import explain_rule

    _seed_rules()
    rules = explain_rule(language="es", category="verbs", level="A1")
    assert len(rules) >= 1
    assert rules[0]["rule_id"] == "es_verb_ser_estar"


def test_explain_rule_no_match():
    from grammar import explain_rule

    assert explain_rule(language="fr", category="verbs", level="A1") == []


def test_generate_exercise():
    from grammar import generate_exercise

    _seed_rules()
    result = generate_exercise(language="es", rule_id="es_verb_ser_estar", count=5)
    assert result["rule"] == "Ser vs Estar"
    assert "prompt" in result


def test_generate_exercise_not_found():
    from grammar import generate_exercise

    result = generate_exercise(language="es", rule_id="nonexistent")
    assert "error" in result


def test_grade_exercise():
    from grammar import grade_exercise

    _seed_rules()
    result = grade_exercise(
        rule_id="es_verb_ser_estar",
        language="es",
        user_answer="Soy alto",
    )
    assert result["rule_id"] == "es_verb_ser_estar"
    assert result["user_answer"] == "Soy alto"
