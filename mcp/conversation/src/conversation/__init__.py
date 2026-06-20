"""
Polyglot Coach — Conversation MCP Service.

Generates roleplay scenarios, evaluates learner dialogue, and suggests
follow-up turns for immersive practice.
"""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import ConversationScenario


def generate_scenario(language: str, level: str, topic: str | None = None) -> dict:
    session = get_session()
    query = session.query(ConversationScenario).filter(
        ConversationScenario.language == language, ConversationScenario.level == level
    )
    if topic:
        query = query.filter(ConversationScenario.title.ilike(f"%{topic}%"))
    scenario = query.first()
    if scenario is None:
        return {
            "language": language,
            "level": level,
            "title": f"Conversation practice ({level})",
            "context": f"Practice your {language} conversation skills at {level} level.",
            "roles": "Learner, Tutor",
            "vocabulary_hints": None,
            "grammar_focus": None,
        }
    return {
        "id": scenario.id,
        "language": scenario.language,
        "title": scenario.title,
        "context": scenario.context,
        "level": scenario.level,
        "roles": scenario.roles,
        "vocabulary_hints": scenario.vocabulary_hints,
        "grammar_focus": scenario.grammar_focus,
    }


def evaluate_response(scenario_id: int, user_turn: str) -> dict:
    session = get_session()
    scenario = session.query(ConversationScenario).filter(ConversationScenario.id == scenario_id).first()
    return {
        "scenario_id": scenario_id,
        "scenario_title": scenario.title if scenario else None,
        "user_turn": user_turn,
        "feedback": "Your response has been recorded for evaluation.",
        "suggestions": [
            "Try using more target-language vocabulary.",
            "Pay attention to grammatical agreement.",
        ],
    }


def suggest_followup(scenario_id: int, conversation_history: list[str]) -> dict:
    session = get_session()
    scenario = session.query(ConversationScenario).filter(ConversationScenario.id == scenario_id).first()
    return {
        "scenario_id": scenario_id,
        "scenario_title": scenario.title if scenario else None,
        "conversation_history": conversation_history,
        "suggested_response": f"Continue the conversation about '{scenario.title if scenario else 'the topic'}'.",
        "vocabulary_hints": scenario.vocabulary_hints.split(",") if scenario and scenario.vocabulary_hints else [],
    }
