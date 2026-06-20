"""Tests for the shared database and models."""


from sqlalchemy import inspect

from polyglot_coach_shared.database import _make_url, get_session, init_db
from polyglot_coach_shared.models import (
    ConversationScenario,
    GrammarRule,
    LearnerProfile,
    LocaleOverride,
    MistakeRecord,
    ProgressRecord,
    ReviewItem,
    VocabularyEntry,
)


def test_make_url_default(monkeypatch):
    monkeypatch.setenv("POLYGLOT_DB_PATH", "/tmp/test_polyglot.db")
    url = _make_url(None)
    assert url == "sqlite:////tmp/test_polyglot.db"


def test_make_url_memory():
    url = _make_url(":memory:")
    assert url == "sqlite://"


def test_init_db_creates_tables():
    engine = init_db(":memory:")
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    expected = {
        "learner_profiles",
        "vocabulary_entries",
        "mistake_records",
        "progress_records",
        "grammar_rules",
        "locale_overrides",
        "review_items",
        "conversation_scenarios",
    }
    assert expected.issubset(set(tables))


def test_get_session_in_memory():
    session = get_session(":memory:")
    assert session is not None
    session.close()


class TestLearnerProfile:
    def test_create_and_query(self):
        session = get_session(":memory:")
        profile = LearnerProfile(
            name="Alice",
            native_language="en",
            target_language="es",
            locale="es_MX",
            proficiency_level="A1",
        )
        session.add(profile)
        session.commit()

        found = session.query(LearnerProfile).filter(LearnerProfile.name == "Alice").first()
        assert found is not None
        assert found.target_language == "es"
        assert found.proficiency_level == "A1"
        session.close()


class TestVocabularyEntry:
    def test_create_and_query(self):
        session = get_session(":memory:")
        profile = LearnerProfile(name="Bob", native_language="en", target_language="fr", locale="fr_FR", proficiency_level="A2")
        session.add(profile)
        session.flush()

        entry = VocabularyEntry(
            profile_id=profile.id,
            word="bonjour",
            translation="hello",
            language="fr",
            context_sentence="Bonjour, comment ça va?",
            tags="greeting,basic",
        )
        session.add(entry)
        session.commit()

        found = session.query(VocabularyEntry).filter(VocabularyEntry.word == "bonjour").first()
        assert found is not None
        assert found.translation == "hello"
        session.close()


class TestMistakeRecord:
    def test_create_and_query(self):
        session = get_session(":memory:")
        profile = LearnerProfile(name="Carlos", native_language="en", target_language="es", locale="neutral", proficiency_level="A1")
        session.add(profile)
        session.flush()

        mistake = MistakeRecord(
            profile_id=profile.id,
            category="grammar",
            user_input="Yo es cansado",
            correction="Yo estoy cansado",
            explanation="Use 'estar' for temporary states",
            context="Talking about being tired",
        )
        session.add(mistake)
        session.commit()

        found = session.query(MistakeRecord).filter(MistakeRecord.profile_id == profile.id).first()
        assert found is not None
        assert found.category == "grammar"
        session.close()


class TestProgressRecord:
    def test_create_and_query(self):
        session = get_session(":memory:")
        profile = LearnerProfile(name="Diana", native_language="en", target_language="de", locale="de_DE", proficiency_level="B1")
        session.add(profile)
        session.flush()

        record = ProgressRecord(
            profile_id=profile.id,
            event_type="lesson_complete",
            detail="Completed lesson 5",
            score=85.0,
        )
        session.add(record)
        session.commit()

        found = session.query(ProgressRecord).filter(ProgressRecord.profile_id == profile.id).first()
        assert found is not None
        assert found.event_type == "lesson_complete"
        assert found.score == 85.0
        session.close()


class TestGrammarRule:
    def test_create_and_query(self):
        session = get_session(":memory:")
        rule = GrammarRule(
            language="es",
            rule_id="es_verb_ser_estar",
            title="Ser vs Estar",
            explanation="Ser is for permanent states, estar is for temporary states.",
            examples="Soy alto.\\nEstoy cansado.",
            level="A1",
            category="verbs",
        )
        session.add(rule)
        session.commit()

        found = session.query(GrammarRule).filter(GrammarRule.rule_id == "es_verb_ser_estar").first()
        assert found is not None
        assert found.title == "Ser vs Estar"
        session.close()


class TestLocaleOverride:
    def test_create_and_query(self):
        session = get_session(":memory:")
        override = LocaleOverride(
            locale="es_MX",
            language="es",
            standard_word="ordenador",
            local_word="computadora",
            notes="Common in Latin America",
        )
        session.add(override)
        session.commit()

        found = session.query(LocaleOverride).filter(LocaleOverride.locale == "es_MX").first()
        assert found is not None
        assert found.local_word == "computadora"
        session.close()


class TestReviewItem:
    def test_create_and_query(self):
        session = get_session(":memory:")
        profile = LearnerProfile(name="Eve", native_language="en", target_language="ja", locale="ja_JP", proficiency_level="N5")
        session.add(profile)
        session.flush()

        item = ReviewItem(
            profile_id=profile.id,
            word="ありがとう",
            language="ja",
            interval=1,
            ease_factor=2.5,
            repetitions=0,
        )
        session.add(item)
        session.commit()

        found = session.query(ReviewItem).filter(ReviewItem.word == "ありがとう").first()
        assert found is not None
        assert found.language == "ja"
        session.close()


class TestConversationScenario:
    def test_create_and_query(self):
        session = get_session(":memory:")
        scenario = ConversationScenario(
            language="fr",
            title="Au restaurant: Commander un repas",
            context="You are at a restaurant in Paris. Order a meal.",
            level="A2",
            roles="Client, Serveur",
            vocabulary_hints="menu, addition, plat",
            grammar_focus="je voudrais, conditionnel",
        )
        session.add(scenario)
        session.commit()

        found = session.query(ConversationScenario).filter(ConversationScenario.language == "fr").first()
        assert found is not None
        assert found.level == "A2"
        session.close()
