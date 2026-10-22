"""Integration checks for the real curriculum packs and loader."""

from __future__ import annotations

import sys
from pathlib import Path

from polyglot_coach_shared.database import _engine_cache, get_session
from polyglot_coach_shared.languages import (
    get_language,
    language_name,
    list_languages,
    load_registry,
    ordered_levels,
)
from polyglot_coach_shared.models import (
    ConversationScenario,
    GrammarRule,
    VocabularyEntry,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CURRICULUM_ROOT = PROJECT_ROOT / "curriculum"

sys.path.insert(0, str(PROJECT_ROOT / "tools"))
from validate_curriculum import validate_curriculum  # noqa: E402


def test_registry_lists_only_shipped_languages():
    registry = load_registry(CURRICULUM_ROOT)
    assert registry["languages"] == ["es", "fr", "de"]
    assert registry["default_language"] == "es"
    assert {pack["code"] for pack in list_languages(CURRICULUM_ROOT)} == {
        "es",
        "fr",
        "de",
    }
    assert get_language("ja", CURRICULUM_ROOT) is None
    assert language_name("es", CURRICULUM_ROOT) == "Spanish"
    assert language_name("xx", CURRICULUM_ROOT) == "xx"


def test_levels_are_returned_in_framework_order():
    assert ordered_levels("es", CURRICULUM_ROOT) == ["A1"]
    assert ordered_levels("fr", CURRICULUM_ROOT) == ["A1"]
    assert ordered_levels("ja", CURRICULUM_ROOT) == []


def test_real_curriculum_passes_validation():
    report = validate_curriculum(CURRICULUM_ROOT)
    assert report.errors == []
    assert set(report.coverage) == {"es", "fr", "de"}
    assert report.coverage["es"]["levels"]["A1"]["words"] == 40
    assert report.coverage["fr"]["levels"]["A1"]["scenarios"] == 3


def test_validator_rejects_unregistered_pack(tmp_path):
    (tmp_path / "registry.yaml").write_text(
        "version: 1\ndefault_language: es\n"
        "level_frameworks:\n  cefr:\n    levels: [A1]\n"
        "languages: [es]\n"
    )
    (tmp_path / "fr").mkdir()
    (tmp_path / "fr" / "language.yaml").write_text(
        "code: fr\nname: French\nnative_name: Français\n"
        "level_framework: cefr\nlevels: [A1]\ndefault_level: A1\n"
        "locales:\n  neutral:\n    name: Neutral\n"
    )
    report = validate_curriculum(tmp_path)
    assert any("not listed in registry" in error for error in report.errors)


def test_validator_rejects_boolean_words(tmp_path):
    (tmp_path / "registry.yaml").write_text(
        "version: 1\ndefault_language: es\n"
        "level_frameworks:\n  cefr:\n    levels: [A1]\n"
        "languages: [es]\n"
    )
    lang = tmp_path / "es"
    (lang / "A1").mkdir(parents=True)
    (lang / "language.yaml").write_text(
        "code: es\nname: Spanish\nnative_name: Español\n"
        "level_framework: cefr\nlevels: [A1]\ndefault_level: A1\n"
        "locales:\n  neutral:\n    name: Neutral\n"
    )
    (lang / "A1" / "vocabulary.yaml").write_text("words:\n  - word: no\n    translation: no\n")
    report = validate_curriculum(tmp_path)
    assert len([error for error in report.errors if "must be a non-empty string" in error]) == 2


def test_loader_seeds_real_curriculum_and_is_idempotent(tmp_path, monkeypatch):
    from polyglot_coach_api.data import loader

    db_path = tmp_path / "curriculum.db"
    monkeypatch.setenv("POLYGLOT_DB_PATH", str(db_path))
    _engine_cache.clear()

    loader.load_all_curriculum_data(CURRICULUM_ROOT)

    session = get_session()
    try:
        languages = {row[0] for row in session.query(VocabularyEntry.language).distinct().all()}
        assert languages == {"es", "fr", "de"}
        counts = {
            "words": session.query(VocabularyEntry).count(),
            "rules": session.query(GrammarRule).count(),
            "scenarios": session.query(ConversationScenario).count(),
        }
    finally:
        session.close()

    assert counts["words"] == 40 + 28 + 27
    assert counts["rules"] == 10 + 3 + 3
    assert counts["scenarios"] == 6 + 3 + 3

    loader.load_all_curriculum_data(CURRICULUM_ROOT)

    session = get_session()
    try:
        assert session.query(VocabularyEntry).count() == counts["words"]
        assert session.query(GrammarRule).count() == counts["rules"]
        assert session.query(ConversationScenario).count() == counts["scenarios"]
    finally:
        session.close()
