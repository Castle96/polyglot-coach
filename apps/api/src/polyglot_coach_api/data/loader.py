"""Load language-pack curriculum data into the shared SQLite database.

``curriculum/registry.yaml`` lists the enabled languages. Each language has a
``language.yaml`` describing its proficiency framework, levels, and locales,
plus one directory per level containing grammar, vocabulary, scenario, and
locale YAML files.

Only languages and levels declared in the registry/pack are loaded. Content in
unregistered directories is ignored; ``tools/validate_curriculum.py`` reports
it so it cannot silently drift.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.languages import get_language, load_registry, ordered_levels
from polyglot_coach_shared.models import (
    ConversationScenario,
    GrammarRule,
    LocaleOverride,
    VocabularyEntry,
)

logger = logging.getLogger(__name__)

CURRICULUM_ROOT = os.environ.get(
    "POLYGLOT_CURRICULUM_PATH",
    str(Path(__file__).resolve().parents[5] / "curriculum"),
)


def load_all_curriculum_data(root: str | Path | None = None) -> None:
    """Seed all registered language packs.

    The loader is idempotent: existing rows are left in place and missing rows
    are added. Validation of pack contents is handled separately by
    ``tools/validate_curriculum.py``.
    """
    curriculum_path = Path(root or CURRICULUM_ROOT)
    if not curriculum_path.exists():
        logger.warning("Curriculum directory does not exist: %s", curriculum_path)
        return

    try:
        registry = load_registry(curriculum_path)
    except FileNotFoundError:
        logger.warning("Curriculum registry not found under %s; skipping seeding", curriculum_path)
        return
    for code in registry.get("languages", []):
        pack = get_language(code, curriculum_path)
        if pack is None:
            logger.warning("Registry lists %r but %s/language.yaml is missing", code, code)
            continue
        if pack.get("code") != code:
            logger.error(
                "Language pack code mismatch: registry=%r language.yaml=%r",
                code,
                pack.get("code"),
            )
            continue

        levels = ordered_levels(code, curriculum_path)
        if not levels:
            logger.warning("Language pack %r declares no enabled levels", code)
            continue

        session = get_session()
        try:
            for level in levels:
                level_dir = curriculum_path / code / level
                if not level_dir.is_dir():
                    logger.warning("Declared level directory is missing: %s", level_dir)
                    continue
                _load_grammar(session, level_dir, code)
                _load_scenarios(session, level_dir, code)
                _load_vocabulary(session, level_dir, code)
                _load_locale_overrides(session, level_dir, code)
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to load curriculum for language %r", code)
            raise
        finally:
            session.close()


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_grammar(session, level_dir: Path, lang: str) -> None:
    path = level_dir / "grammar.yaml"
    if not path.exists():
        return
    data = _read_yaml(path)
    for rule in data.get("rules", []):
        exists = session.query(GrammarRule).filter(GrammarRule.rule_id == rule["rule_id"]).first()
        if exists:
            continue
        rule.setdefault("language", lang)
        session.add(GrammarRule(**rule))


def _load_scenarios(session, level_dir: Path, lang: str) -> None:
    path = level_dir / "scenarios.yaml"
    if not path.exists():
        return
    data = _read_yaml(path)
    for scenario in data.get("scenarios", []):
        exists = (
            session.query(ConversationScenario)
            .filter(
                ConversationScenario.title == scenario["title"],
                ConversationScenario.language == lang,
            )
            .first()
        )
        if exists:
            continue
        scenario.setdefault("language", lang)
        session.add(ConversationScenario(**scenario))


def _load_vocabulary(session, level_dir: Path, lang: str) -> None:
    path = level_dir / "vocabulary.yaml"
    if not path.exists():
        return
    data = _read_yaml(path)
    for word in data.get("words", []):
        exists = (
            session.query(VocabularyEntry)
            .filter(
                VocabularyEntry.word == word["word"],
                VocabularyEntry.language == lang,
            )
            .first()
        )
        if exists:
            continue
        session.add(
            VocabularyEntry(
                word=word["word"],
                translation=word["translation"],
                language=lang,
                profile_id=0,
                tags=word.get("tags", ""),
            )
        )


def _load_locale_overrides(session, level_dir: Path, lang: str) -> None:
    path = level_dir / "locale.yaml"
    if not path.exists():
        return
    data = _read_yaml(path)
    for override in data.get("locale_overrides", []):
        exists = (
            session.query(LocaleOverride)
            .filter(
                LocaleOverride.locale == override["locale"],
                LocaleOverride.standard_word == override["standard_word"],
            )
            .first()
        )
        if exists:
            continue
        override.setdefault("language", lang)
        session.add(LocaleOverride(**override))
