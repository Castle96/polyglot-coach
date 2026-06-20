"""Tests for the curriculum MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import ConversationScenario


def _seed_scenarios():
    session = get_session(":memory:")
    session.add_all([
        ConversationScenario(
            language="fr",
            title="Au restaurant: Commander un repas",
            context="You are at a restaurant. Order a meal.",
            level="A2",
            roles="Client, Serveur",
        ),
        ConversationScenario(
            language="fr",
            title="À l'hôtel: Réserver une chambre",
            context="Book a hotel room.",
            level="A2",
            roles="Client, Réceptionniste",
        ),
        ConversationScenario(
            language="es",
            title="En el restaurante: Pedir comida",
            context="Order food at a restaurant.",
            level="A1",
            roles="Cliente, Camarero",
        ),
    ])
    session.commit()
    session.close()


def test_get_lesson():
    from curriculum import get_lesson

    _seed_scenarios()
    result = get_lesson(language="fr", level="A2")
    assert result["language"] == "fr"
    assert len(result["scenarios"]) == 2


def test_get_lesson_empty():
    from curriculum import get_lesson

    result = get_lesson(language="de", level="C1")
    assert result["language"] == "de"
    assert result["scenarios"] == []


def test_get_topic():
    from curriculum import get_topic

    _seed_scenarios()
    result = get_topic(language="es")
    assert result["language"] == "es"
    assert "En el restaurante" in result["topics"]


def test_get_scenario_found():
    from curriculum import get_scenario

    _seed_scenarios()
    scenario = get_scenario(scenario_id=1)
    assert scenario is not None
    assert "language" in scenario


def test_get_scenario_not_found():
    from curriculum import get_scenario

    assert get_scenario(scenario_id=999) is None
