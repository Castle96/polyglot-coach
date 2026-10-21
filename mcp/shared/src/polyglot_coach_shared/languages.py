"""Access to the curriculum language registry.

The registry is the single source of truth for which languages are enabled,
which proficiency framework and levels they use, and which locales and
capabilities they expose. Both the API and MCP services read from it so that
adding a language does not require hardcoding it in Python.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


def curriculum_root(root: str | Path | None = None) -> Path:
    """Return the curriculum directory, preferring an explicit path."""
    if root is not None:
        return Path(root)
    env_root = os.environ.get("POLYGLOT_CURRICULUM_PATH")
    if env_root:
        return Path(env_root)
    # .../mcp/shared/src/polyglot_coach_shared/languages.py -> repository root
    return Path(__file__).resolve().parents[4] / "curriculum"


@lru_cache(maxsize=8)
def _load_registry_cached(root_str: str) -> dict[str, Any]:
    path = Path(root_str) / "registry.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Curriculum registry not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Curriculum registry must be a mapping: {path}")
    return data


def load_registry(root: str | Path | None = None) -> dict[str, Any]:
    """Load and cache ``curriculum/registry.yaml``."""
    return _load_registry_cached(str(curriculum_root(root)))


@lru_cache(maxsize=64)
def _load_language_cached(root_str: str, code: str) -> dict[str, Any] | None:
    path = Path(root_str) / code / "language.yaml"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Language pack must be a mapping: {path}")
    return data


def get_language(code: str, root: str | Path | None = None) -> dict[str, Any] | None:
    """Return a language pack, or ``None`` when it is not defined."""
    return _load_language_cached(str(curriculum_root(root)), code)


def list_languages(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Return enabled language packs in registry order."""
    registry = load_registry(root)
    languages = []
    for code in registry.get("languages", []):
        pack = get_language(code, root)
        if pack is not None:
            languages.append(pack)
    return languages


def language_name(code: str, root: str | Path | None = None) -> str:
    """Return the English display name for ``code``, falling back to the code."""
    pack = get_language(code, root)
    if pack:
        return str(pack.get("name") or code)
    return code


def level_framework(code: str, root: str | Path | None = None) -> dict[str, Any] | None:
    """Return the proficiency framework used by a language."""
    pack = get_language(code, root)
    if not pack:
        return None
    framework = pack.get("level_framework")
    if not framework:
        return None
    return load_registry(root).get("level_frameworks", {}).get(framework)


def ordered_levels(code: str, root: str | Path | None = None) -> list[str]:
    """Return a language's enabled levels in framework order."""
    pack = get_language(code, root)
    if not pack:
        return []
    enabled = list(pack.get("levels", []))
    framework = level_framework(code, root) or {}
    order = list(framework.get("levels", []))
    if not order:
        return enabled
    return [level for level in order if level in enabled]


def clear_cache() -> None:
    """Clear cached registry and language packs (used by tests and reloads)."""
    _load_registry_cached.cache_clear()
    _load_language_cached.cache_clear()


def _public_locales(pack: dict[str, Any]) -> list[dict[str, Any]]:
    locales = pack.get("locales") or {}
    items: list[dict[str, Any]] = []
    for code, data in locales.items():
        if not isinstance(data, dict):
            data = {}
        items.append(
            {
                "code": code,
                "name": data.get("name") or code,
                "stt_language": data.get("stt_language"),
                "tts_voice": data.get("tts_voice"),
            }
        )
    return sorted(items, key=lambda item: (item["code"] != "neutral", item["code"]))


def features_for(
    code: str, level: str | None = None, root: str | Path | None = None
) -> list[dict[str, Any]]:
    """Return language features, optionally filtered to those valid at ``level``."""
    pack = get_language(code, root)
    if not pack:
        return []
    features = pack.get("features") or []
    if level is None:
        return list(features)
    return [
        feature
        for feature in features
        if not feature.get("levels") or level in feature.get("levels", [])
    ]


def get_feature(
    code: str, feature_id: str, root: str | Path | None = None
) -> dict[str, Any] | None:
    """Return a single feature by id."""
    for feature in features_for(code, root=root):
        if feature.get("id") == feature_id:
            return feature
    return None


def public_language(code: str, root: str | Path | None = None) -> dict[str, Any] | None:
    """Return the client-facing representation of a language pack."""
    pack = get_language(code, root)
    if not pack:
        return None
    framework_id = pack.get("level_framework")
    framework: dict[str, Any] = {}
    locales = pack.get("locales") or {}
    try:
        framework = load_registry(root).get("level_frameworks", {}).get(framework_id, {})
    except FileNotFoundError:
        pass
    return {
        "code": code,
        "name": pack.get("name") or code,
        "native_name": pack.get("native_name") or pack.get("name") or code,
        "status": pack.get("status", "active"),
        "script": pack.get("script"),
        "direction": pack.get("direction", "ltr"),
        "level_framework": framework_id,
        "level_framework_name": framework.get("name") or framework_id,
        "framework_levels": framework.get("levels", []),
        "levels": ordered_levels(code, root) or list(pack.get("levels", [])),
        "default_level": pack.get("default_level"),
        "locales": _public_locales(pack),
        "default_locale": "neutral" if "neutral" in locales else next(iter(locales), None),
        "capabilities": list(pack.get("capabilities", [])),
        "features": features_for(code, root=root),
        "teaching_notes": list(pack.get("teaching_notes", [])),
        "notes": pack.get("notes"),
    }


def list_public_languages(root: str | Path | None = None) -> list[dict[str, Any]]:
    """Return client-facing metadata for every enabled language."""
    return [
        data
        for code in load_registry(root).get("languages", [])
        if (data := public_language(code, root)) is not None
    ]


def resolve_selection(
    code: str,
    level: str | None = None,
    locale: str | None = None,
    features: list[str] | None = None,
    root: str | Path | None = None,
) -> tuple[dict[str, Any], str, str]:
    """Resolve and validate a language/level/locale/feature selection.

    Returns ``(pack, level, locale)``. Raises :class:`ValueError` with a
    human-readable message when the selection is not supported.
    """
    pack = get_language(code, root)
    if not pack:
        try:
            enabled = ", ".join(load_registry(root).get("languages", []))
        except FileNotFoundError:
            enabled = ""
        suffix = f" Enabled languages: {enabled}." if enabled else ""
        raise ValueError(f"Unsupported language '{code}'.{suffix}")

    levels = ordered_levels(code, root) or list(pack.get("levels", []))
    resolved_level = level or pack.get("default_level") or (levels[0] if levels else None)
    if not resolved_level or resolved_level not in levels:
        raise ValueError(
            f"Level '{resolved_level}' is not available for {pack.get('name', code)}. "
            f"Valid levels: {', '.join(levels) or 'none'}."
        )

    locales = pack.get("locales") or {}
    resolved_locale = locale or ("neutral" if "neutral" in locales else next(iter(locales), None))
    if not resolved_locale or resolved_locale not in locales:
        raise ValueError(
            f"Locale '{resolved_locale}' is not available for {pack.get('name', code)}. "
            f"Valid locales: {', '.join(locales) or 'none'}."
        )

    available_features = {
        feature.get("id") for feature in features_for(code, resolved_level, root)
    }
    requested = features or []
    invalid = [feature for feature in requested if feature not in available_features]
    if invalid:
        raise ValueError(
            f"Feature(s) not available at {resolved_level} for "
            f"{pack.get('name', code)}: {', '.join(invalid)}."
        )

    return pack, resolved_level, resolved_locale
