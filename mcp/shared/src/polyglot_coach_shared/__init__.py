"""
Polyglot Coach — Shared Models & Database Utilities.

Provides SQLAlchemy base, models, and session management shared
across all MCP services.
"""

from polyglot_coach_shared.database import get_session, init_db
from polyglot_coach_shared.models import (
    Base,
    ConversationScenario,
    GrammarRule,
    LearnerProfile,
    LocaleOverride,
    MistakeRecord,
    ProgressRecord,
    ReviewItem,
    VocabularyEntry,
)

__all__ = [
    "Base",
    "ConversationScenario",
    "get_session",
    "GrammarRule",
    "init_db",
    "LearnerProfile",
    "LocaleOverride",
    "MistakeRecord",
    "ProgressRecord",
    "ReviewItem",
    "VocabularyEntry",
]
