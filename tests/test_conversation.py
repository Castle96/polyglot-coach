"""Tests for the conversation MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import ConversationScenario


def _seed_scenarios():
    session = get_session(":memory:")
    session.add_all([
        ConversationScenario(
            language="fr",
            title="Au restaurant",
            context="Order a meal at a restaurant.",
            level="A2",
            roles="Client, Serveur",
            vocabulary_hints="menu, addition, plat",
            grammar_focus="je voudrais",
        ),
        ConversationScenario(
            language="es",
            title="En el mercado",
            context="Buy fruits at the market.",
            level="A1",
            roles="Cliente, Vendedor",
            vocabulary_hints="manzana, plátano, precio",
            grammar_focus="quisiera, cuánto cuesta",
        ),
    ])
    session.commit()
    session.close()


def test_generate_scenario():
    from conversation import generate_scenario

    _seed_scenarios()
    scenario = generate_scenario(language="fr", level="A2")
    assert scenario["title"] == "Au restaurant"
    assert scenario["context"] is not None


def test_generate_scenario_fallback():
    from conversation import generate_scenario

    scenario = generate_scenario(language="de", level="C1")
    assert "title" in scenario
    assert "Practice your" in scenario["context"]


def test_generate_scenario_with_topic():
    from conversation import generate_scenario

    _seed_scenarios()
    scenario = generate_scenario(language="fr", level="A2", topic="restaurant")
    assert scenario is not None


def test_evaluate_response():
    from conversation import evaluate_response

    _seed_scenarios()
    result = evaluate_response(scenario_id=1, user_turn="Je voudrais un café")
    assert result["scenario_id"] == 1
    assert result["user_turn"] == "Je voudrais un café"


def test_evaluate_response_nonexistent():
    from conversation import evaluate_response

    result = evaluate_response(scenario_id=999, user_turn="Hello")
    assert result["scenario_id"] == 999


def test_suggest_followup():
    from conversation import suggest_followup

    _seed_scenarios()
    result = suggest_followup(scenario_id=1, conversation_history=["Bonjour", "Je voudrais un café"])
    assert result["scenario_id"] == 1
    assert len(result["conversation_history"]) == 2
