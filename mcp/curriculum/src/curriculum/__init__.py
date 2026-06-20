"""
Polyglot Coach — Curriculum MCP Service.

Selects lessons, topics, objectives, and scenario content based on
language, locale, and learner proficiency.
"""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import ConversationScenario


def get_lesson(language: str, level: str) -> dict:
    session = get_session()
    scenarios = (
        session.query(ConversationScenario)
        .filter(ConversationScenario.language == language, ConversationScenario.level == level)
        .all()
    )
    return {
        "language": language,
        "level": level,
        "scenarios": [
            {
                "id": s.id,
                "title": s.title,
                "context": s.context,
                "roles": s.roles,
                "vocabulary_hints": s.vocabulary_hints,
                "grammar_focus": s.grammar_focus,
            }
            for s in scenarios
        ],
    }


def get_topic(language: str, level: str | None = None) -> dict:
    session = get_session()
    query = session.query(ConversationScenario).filter(ConversationScenario.language == language)
    if level:
        query = query.filter(ConversationScenario.level == level)
    scenarios = query.all()
    topics: dict[str, list[dict]] = {}
    for s in scenarios:
        topic = s.title.split(":")[0].strip() if ":" in s.title else s.title
        if topic not in topics:
            topics[topic] = []
        topics[topic].append(
            {
                "id": s.id,
                "title": s.title,
                "level": s.level,
                "context": s.context,
            }
        )
    return {"language": language, "topics": topics}


def get_scenario(scenario_id: int) -> dict | None:
    session = get_session()
    scenario = session.query(ConversationScenario).filter(ConversationScenario.id == scenario_id).first()
    if scenario is None:
        return None
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
