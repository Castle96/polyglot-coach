"""
Loads curriculum YAML data into the shared SQLite database.

Scans `CURRICULUM_ROOT` (default: `curriculum/` at project root) for
language directories, reads manifest and level YAML files, and seeds
the database on first run.
"""

import os
from pathlib import Path

import yaml

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import (
    ConversationScenario,
    GrammarRule,
    LocaleOverride,
    VocabularyEntry,
)

CURRICULUM_ROOT = os.environ.get(
    "POLYGLOT_CURRICULUM_PATH",
    str(Path(__file__).resolve().parents[5] / "curriculum"),
)


def load_all_curriculum_data():
    root = Path(CURRICULUM_ROOT)
    if not root.exists():
        return
    for lang_dir in sorted(root.iterdir()):
        if not lang_dir.is_dir():
            continue
        manifest = lang_dir / "manifest.yaml"
        if not manifest.exists():
            continue
        with open(manifest) as f:
            manifest_data = yaml.safe_load(f) or {}
        lang = manifest_data.get("language", lang_dir.name)
        for level_dir in sorted(lang_dir.iterdir()):
            if not level_dir.is_dir():
                continue
            _load_grammar(level_dir, lang)
            _load_scenarios(level_dir, lang)
            _load_vocabulary(level_dir, lang)
            _load_locale_overrides(level_dir, lang)


def _load_grammar(level_dir: Path, lang: str):
    path = level_dir / "grammar.yaml"
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data or "rules" not in data:
        return
    session = get_session()
    for rule in data["rules"]:
        exists = session.query(GrammarRule).filter(GrammarRule.rule_id == rule["rule_id"]).first()
        if exists:
            continue
        rule.setdefault("language", lang)
        session.add(GrammarRule(**rule))
    session.commit()
    session.close()


def _load_scenarios(level_dir: Path, lang: str):
    path = level_dir / "scenarios.yaml"
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data or "scenarios" not in data:
        return
    session = get_session()
    for sc in data["scenarios"]:
        exists = (
            session.query(ConversationScenario)
            .filter(
                ConversationScenario.title == sc["title"],
                ConversationScenario.language == lang,
            )
            .first()
        )
        if exists:
            continue
        sc.setdefault("language", lang)
        session.add(ConversationScenario(**sc))
    session.commit()
    session.close()


def _load_vocabulary(level_dir: Path, lang: str):
    path = level_dir / "vocabulary.yaml"
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data or "words" not in data:
        return
    session = get_session()
    for w in data["words"]:
        tags = w.get("tags", "")
        exists = (
            session.query(VocabularyEntry)
            .filter(
                VocabularyEntry.word == w["word"],
                VocabularyEntry.language == lang,
            )
            .first()
        )
        if exists:
            continue
        session.add(
            VocabularyEntry(
                word=w["word"],
                translation=w["translation"],
                language=lang,
                profile_id=0,
                tags=tags,
            )
        )
    session.commit()
    session.close()


def _load_locale_overrides(level_dir: Path, lang: str):
    path = level_dir / "locale.yaml"
    if not path.exists():
        return
    with open(path) as f:
        data = yaml.safe_load(f)
    if not data:
        return
    session = get_session()
    for ov in data.get("locale_overrides", []):
        exists = (
            session.query(LocaleOverride)
            .filter(
                LocaleOverride.locale == ov["locale"],
                LocaleOverride.standard_word == ov["standard_word"],
            )
            .first()
        )
        if exists:
            continue
        ov.setdefault("language", lang)
        session.add(LocaleOverride(**ov))
    session.commit()
    session.close()
