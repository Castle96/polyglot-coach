from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class LearnerProfile(Base):
    __tablename__ = "learner_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    native_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    locale = Column(String(10), nullable=False, default="neutral")
    proficiency_level = Column(String(5), nullable=False, default="A1")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    mistakes = relationship("MistakeRecord", back_populates="profile", cascade="all, delete-orphan")
    progress = relationship("ProgressRecord", back_populates="profile", cascade="all, delete-orphan")
    review_items = relationship("ReviewItem", back_populates="profile", cascade="all, delete-orphan")
    vocabulary = relationship("VocabularyEntry", back_populates="profile", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="profile", cascade="all, delete-orphan")


class VocabularyEntry(Base):
    __tablename__ = "vocabulary_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False)
    word = Column(String(200), nullable=False)
    translation = Column(String(200), nullable=False)
    language = Column(String(10), nullable=False)
    context_sentence = Column(Text, nullable=True)
    tags = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("LearnerProfile", back_populates="vocabulary")


class MistakeRecord(Base):
    __tablename__ = "mistake_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False)
    category = Column(String(50), nullable=False)
    user_input = Column(Text, nullable=False)
    correction = Column(Text, nullable=False)
    explanation = Column(Text, nullable=True)
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("LearnerProfile", back_populates="mistakes")


class ProgressRecord(Base):
    __tablename__ = "progress_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    detail = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("LearnerProfile", back_populates="progress")


class GrammarRule(Base):
    __tablename__ = "grammar_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    language = Column(String(10), nullable=False)
    rule_id = Column(String(100), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    explanation = Column(Text, nullable=False)
    examples = Column(Text, nullable=True)
    level = Column(String(5), nullable=False)
    category = Column(String(50), nullable=False)


class LocaleOverride(Base):
    __tablename__ = "locale_overrides"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locale = Column(String(10), nullable=False)
    language = Column(String(10), nullable=False)
    standard_word = Column(String(200), nullable=False)
    local_word = Column(String(200), nullable=False)
    notes = Column(Text, nullable=True)


class ReviewItem(Base):
    __tablename__ = "review_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False)
    word = Column(String(200), nullable=False)
    language = Column(String(10), nullable=False)
    interval = Column(Integer, nullable=False, default=1)
    ease_factor = Column(Float, nullable=False, default=2.5)
    repetitions = Column(Integer, nullable=False, default=0)
    next_review_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    profile = relationship("LearnerProfile", back_populates="review_items")


class ConversationScenario(Base):
    __tablename__ = "conversation_scenarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    language = Column(String(10), nullable=False)
    title = Column(String(200), nullable=False)
    context = Column(Text, nullable=False)
    level = Column(String(5), nullable=False)
    roles = Column(String(500), nullable=True)
    vocabulary_hints = Column(Text, nullable=True)
    grammar_focus = Column(Text, nullable=True)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    profile_id = Column(Integer, ForeignKey("learner_profiles.id"), nullable=False)
    title = Column(String(200), nullable=False)
    language = Column(String(10), nullable=False)
    state = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    profile = relationship("LearnerProfile", back_populates="sessions")
