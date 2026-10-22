#!/usr/bin/env python3
"""Validate Polyglot Coach language packs.

Checks that the registry, per-language metadata, and level content agree with
each other before the API seeds them into SQLite. Run it locally and in CI:

    uv run python tools/validate_curriculum.py
    uv run python tools/validate_curriculum.py --strict
    uv run python tools/validate_curriculum.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "curriculum"

LEVEL_DIR_RE = re.compile(r"^(A[12]|B[12]|C[12]|N[1-5])$")
VALID_STATUSES = {"active", "preview", "draft"}
PLACEHOLDER_MARKERS = (
    "example scenario",
    "describe the scenario here",
    "example grammar rule",
    "explain the rule here",
    "grammar-rule-id-1",
)


@dataclass
class ValidationReport:
    root: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    coverage: dict[str, dict[str, Any]] = field(default_factory=dict)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warning(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _load_yaml(path: Path, report: ValidationReport) -> Any:
    try:
        with open(path, encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as exc:
        report.error(f"{path}: invalid YAML — {exc}")
        return None


def _require_mapping(value: Any, label: str, report: ValidationReport) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        report.error(f"{label}: expected a mapping")
        return None
    return value


def _require_list(value: Any, label: str, report: ValidationReport) -> list[Any] | None:
    if not isinstance(value, list):
        report.error(f"{label}: expected a list")
        return None
    return value


def _require_strings(value: Any, label: str, report: ValidationReport) -> list[str] | None:
    items = _require_list(value, label, report)
    if items is None:
        return None
    if not all(isinstance(item, str) and item.strip() for item in items):
        report.error(f"{label}: every entry must be a non-empty string")
        return None
    return items


def validate_curriculum(root: str | Path = DEFAULT_ROOT) -> ValidationReport:
    """Validate every registered language pack under ``root``."""
    report = ValidationReport(root=Path(root).resolve())
    registry_path = report.root / "registry.yaml"
    if not registry_path.exists():
        report.error(f"{registry_path}: missing curriculum registry")
        return report

    registry = _require_mapping(_load_yaml(registry_path, report), str(registry_path), report)
    if registry is None:
        return report

    if registry.get("version") != 1:
        report.error(f"{registry_path}: version must be 1")

    frameworks = (
        _require_mapping(
            registry.get("level_frameworks", {}),
            f"{registry_path}: level_frameworks",
            report,
        )
        or {}
    )
    framework_levels: dict[str, list[str]] = {}
    for name, framework in frameworks.items():
        data = _require_mapping(framework, f"{registry_path}: framework {name}", report)
        if data is None:
            continue
        levels = _require_strings(
            data.get("levels"), f"{registry_path}: framework {name}.levels", report
        )
        if levels is None:
            continue
        if len(set(levels)) != len(levels):
            report.error(f"{registry_path}: framework {name} contains duplicate levels")
        framework_levels[name] = levels

    active_codes = (
        _require_strings(registry.get("languages"), f"{registry_path}: languages", report) or []
    )
    if not active_codes:
        report.error(f"{registry_path}: no languages are enabled")
    if len(set(active_codes)) != len(active_codes):
        report.error(f"{registry_path}: duplicate language codes in languages")

    default_language = registry.get("default_language")
    if default_language and default_language not in active_codes:
        report.error(
            f"{registry_path}: default_language {default_language!r} is not an enabled language"
        )

    planned_codes: set[str] = set()
    planned = registry.get("planned_languages") or []
    for entry in _require_list(planned, f"{registry_path}: planned_languages", report) or []:
        data = _require_mapping(entry, f"{registry_path}: planned language", report)
        if data is None:
            continue
        code = data.get("code")
        if not isinstance(code, str) or not code:
            report.error(f"{registry_path}: planned language is missing a code")
            continue
        planned_codes.add(code)
        if code in active_codes:
            report.error(f"{registry_path}: {code!r} is both active and planned")
        if data.get("level_framework") not in framework_levels:
            report.error(
                f"{registry_path}: planned language {code!r} uses unknown framework "
                f"{data.get('level_framework')!r}"
            )

    if planned_codes & set(active_codes):
        report.error(f"{registry_path}: active and planned languages overlap")

    # Detect unregistered language directories before loading the enabled ones.
    for child in sorted(report.root.iterdir()):
        if not child.is_dir() or child.name.startswith(".") or child.name == "common":
            continue
        pack_path = child / "language.yaml"
        legacy_path = child / "manifest.yaml"
        if legacy_path.exists():
            report.error(f"{legacy_path}: legacy manifest.yaml — use language.yaml")
        if pack_path.exists() and child.name not in active_codes:
            if child.name in planned_codes:
                report.error(
                    f"{pack_path}: planned language must not have a pack until it is enabled"
                )
            else:
                report.error(f"{pack_path}: language pack is not listed in registry languages")
        elif not pack_path.exists():
            level_dirs = [
                entry
                for entry in child.iterdir()
                if entry.is_dir() and LEVEL_DIR_RE.match(entry.name)
            ]
            if level_dirs:
                report.error(f"{child}: level content exists but no language.yaml is present")

    seen_codes: set[str] = set()
    seen_rule_ids: set[str] = set()
    for code in active_codes:
        if code in seen_codes:
            continue
        seen_codes.add(code)
        pack = _validate_language_pack(
            report,
            code,
            framework_levels,
            seen_rule_ids,
        )
        if pack is not None:
            report.coverage[code] = pack

    return report


def _validate_language_pack(
    report: ValidationReport,
    code: str,
    framework_levels: dict[str, list[str]],
    seen_rule_ids: set[str],
) -> dict[str, Any] | None:
    lang_dir = report.root / code
    pack_path = lang_dir / "language.yaml"
    if not pack_path.exists():
        report.error(f"{pack_path}: missing language pack")
        return None

    pack = _require_mapping(_load_yaml(pack_path, report), str(pack_path), report)
    if pack is None:
        return None

    if pack.get("code") != code:
        report.error(f"{pack_path}: code must be {code!r}, got {pack.get('code')!r}")
    for field_name in ("name", "native_name"):
        value = pack.get(field_name)
        if not isinstance(value, str) or not value.strip():
            report.error(f"{pack_path}: {field_name} must be a non-empty string")

    status = pack.get("status", "active")
    if status not in VALID_STATUSES:
        report.error(f"{pack_path}: status must be one of {sorted(VALID_STATUSES)}")

    framework_name = pack.get("level_framework")
    if framework_name not in framework_levels:
        report.error(
            f"{pack_path}: unknown level_framework {framework_name!r}; "
            f"expected one of {sorted(framework_levels)}"
        )
        framework_order: list[str] = []
    else:
        framework_order = framework_levels[framework_name]

    levels = _require_strings(pack.get("levels"), f"{pack_path}: levels", report) or []
    if not levels:
        report.error(f"{pack_path}: at least one level is required")
    if len(set(levels)) != len(levels):
        report.error(f"{pack_path}: duplicate levels")
    for level in levels:
        if framework_order and level not in framework_order:
            report.error(
                f"{pack_path}: level {level!r} is not part of framework {framework_name!r}"
            )
        if not LEVEL_DIR_RE.match(level):
            report.error(f"{pack_path}: level {level!r} is not a recognised level name")
    default_level = pack.get("default_level")
    if default_level not in levels:
        report.error(f"{pack_path}: default_level {default_level!r} is not in levels")

    locales = _require_mapping(pack.get("locales", {}), f"{pack_path}: locales", report) or {}
    if not locales:
        report.error(f"{pack_path}: at least one locale is required")
    if "neutral" not in locales:
        report.warning(f"{pack_path}: no 'neutral' locale declared")
    for locale, locale_data in locales.items():
        if not isinstance(locale, str) or not locale:
            report.error(f"{pack_path}: locale keys must be non-empty strings")
            continue
        data = _require_mapping(locale_data, f"{pack_path}: locale {locale}", report)
        if data is None:
            continue
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            report.error(f"{pack_path}: locale {locale} is missing a name")
        for key in ("stt_language", "tts_voice"):
            if key in data and not isinstance(data[key], str):
                report.error(f"{pack_path}: locale {locale}.{key} must be a string")

    capabilities = pack.get("capabilities")
    if capabilities is not None:
        _require_strings(capabilities, f"{pack_path}: capabilities", report)

    script = pack.get("script")
    if script is not None and (not isinstance(script, str) or not script.strip()):
        report.error(f"{pack_path}: script must be a non-empty string when present")
    direction = pack.get("direction", "ltr")
    if not isinstance(direction, str) or direction not in {"ltr", "rtl"}:
        report.error(f"{pack_path}: direction must be 'ltr' or 'rtl'")
    teaching_notes = pack.get("teaching_notes")
    if teaching_notes is not None:
        _require_strings(teaching_notes, f"{pack_path}: teaching_notes", report)

    feature_count = 0
    features = pack.get("features")
    if features is not None:
        feature_items = _require_list(features, f"{pack_path}: features", report) or []
        feature_count = len(feature_items)
        seen_feature_ids: set[str] = set()
        for index, item in enumerate(feature_items):
            label = f"{pack_path}: features[{index}]"
            feature = _require_mapping(item, label, report)
            if feature is None:
                continue
            for key in ("id", "name", "category", "description"):
                if not isinstance(feature.get(key), str) or not feature[key].strip():
                    report.error(f"{label}: {key} must be a non-empty string")
            feature_id = feature.get("id")
            if isinstance(feature_id, str):
                if not re.fullmatch(r"[a-z0-9_]+", feature_id):
                    report.error(
                        f"{label}: id {feature_id!r} must use lowercase letters, digits, "
                        "and underscores"
                    )
                if feature_id in seen_feature_ids:
                    report.error(f"{label}: duplicate feature id {feature_id!r}")
                seen_feature_ids.add(feature_id)
            feature_levels = feature.get("levels")
            if feature_levels is not None:
                levels_value = _require_strings(feature_levels, f"{label}: levels", report) or []
                for feature_level in levels_value:
                    if feature_level not in levels:
                        report.error(
                            f"{label}: level {feature_level!r} is not declared in language.yaml"
                        )
            examples = feature.get("examples")
            if examples is not None:
                _require_strings(examples, f"{label}: examples", report)

    level_order = [level for level in framework_order if level in levels] or levels
    level_results: dict[str, Any] = {}
    seen_words: set[str] = set()
    seen_titles: set[str] = set()

    actual_level_dirs = {
        entry.name
        for entry in lang_dir.iterdir()
        if entry.is_dir() and LEVEL_DIR_RE.match(entry.name)
    }
    for extra in sorted(actual_level_dirs - set(levels)):
        report.error(f"{lang_dir / extra}: level directory is not declared in language.yaml")

    for level in level_order:
        level_dir = lang_dir / level
        if not level_dir.is_dir():
            report.error(f"{level_dir}: declared level directory is missing")
            continue
        result = _validate_level(
            report,
            code,
            level,
            level_dir,
            locales,
            seen_rule_ids,
            seen_words,
            seen_titles,
        )
        level_results[level] = result

    return {
        "name": pack.get("name"),
        "level_framework": framework_name,
        "status": status,
        "features": feature_count,
        "levels": level_results,
    }


def _validate_level(
    report: ValidationReport,
    code: str,
    level: str,
    level_dir: Path,
    locales: dict[str, Any],
    seen_rule_ids: set[str],
    seen_words: set[str],
    seen_titles: set[str],
) -> dict[str, int]:
    counts = {"rules": 0, "words": 0, "scenarios": 0, "locale_overrides": 0, "files": 0}

    grammar_path = level_dir / "grammar.yaml"
    if grammar_path.exists():
        counts["files"] += 1
        data = _require_mapping(_load_yaml(grammar_path, report), str(grammar_path), report) or {}
        rules = _require_list(data.get("rules", []), f"{grammar_path}: rules", report) or []
        counts["rules"] = len(rules)
        for index, item in enumerate(rules):
            label = f"{grammar_path}: rules[{index}]"
            rule = _require_mapping(item, label, report)
            if rule is None:
                continue
            for key in ("rule_id", "title", "explanation", "level", "category"):
                if not isinstance(rule.get(key), str) or not rule[key].strip():
                    report.error(f"{label}: {key} must be a non-empty string")
            rule_id = rule.get("rule_id")
            if isinstance(rule_id, str):
                expected_prefix = f"{code}_{level}_"
                if not rule_id.startswith(expected_prefix):
                    report.error(
                        f"{label}: rule_id {rule_id!r} must start with {expected_prefix!r}"
                    )
                if rule_id in seen_rule_ids:
                    report.error(f"{label}: duplicate rule_id {rule_id!r} across curriculum")
                seen_rule_ids.add(rule_id)
            if rule.get("level") != level:
                report.error(f"{label}: level must be {level!r}, got {rule.get('level')!r}")
            if _is_placeholder(rule.get("title")):
                report.warning(f"{label}: placeholder grammar rule {rule.get('title')!r}")

    vocabulary_path = level_dir / "vocabulary.yaml"
    if vocabulary_path.exists():
        counts["files"] += 1
        data = (
            _require_mapping(_load_yaml(vocabulary_path, report), str(vocabulary_path), report)
            or {}
        )
        words = _require_list(data.get("words", []), f"{vocabulary_path}: words", report) or []
        counts["words"] = len(words)
        for index, item in enumerate(words):
            label = f"{vocabulary_path}: words[{index}]"
            word = _require_mapping(item, label, report)
            if word is None:
                continue
            for key in ("word", "translation"):
                if not isinstance(word.get(key), str) or not word[key].strip():
                    report.error(f"{label}: {key} must be a non-empty string")
            value = word.get("word")
            if isinstance(value, str):
                normalised = value.strip().casefold()
                if normalised in seen_words:
                    report.error(f"{label}: duplicate word {value!r} in language {code!r}")
                seen_words.add(normalised)

    scenarios_path = level_dir / "scenarios.yaml"
    if scenarios_path.exists():
        counts["files"] += 1
        data = (
            _require_mapping(_load_yaml(scenarios_path, report), str(scenarios_path), report) or {}
        )
        scenarios = (
            _require_list(data.get("scenarios", []), f"{scenarios_path}: scenarios", report) or []
        )
        counts["scenarios"] = len(scenarios)
        for index, item in enumerate(scenarios):
            label = f"{scenarios_path}: scenarios[{index}]"
            scenario = _require_mapping(item, label, report)
            if scenario is None:
                continue
            for key in ("title", "context", "level"):
                if not isinstance(scenario.get(key), str) or not scenario[key].strip():
                    report.error(f"{label}: {key} must be a non-empty string")
            title = scenario.get("title")
            if isinstance(title, str):
                if title in seen_titles:
                    report.error(f"{label}: duplicate scenario title {title!r}")
                seen_titles.add(title)
            if scenario.get("level") != level:
                report.error(f"{label}: level must be {level!r}, got {scenario.get('level')!r}")
            if _is_placeholder(title) or _is_placeholder(scenario.get("context")):
                report.warning(f"{label}: placeholder scenario content")

    locale_path = level_dir / "locale.yaml"
    if locale_path.exists():
        counts["files"] += 1
        data = _require_mapping(_load_yaml(locale_path, report), str(locale_path), report) or {}
        overrides = (
            _require_list(
                data.get("locale_overrides", []),
                f"{locale_path}: locale_overrides",
                report,
            )
            or []
        )
        counts["locale_overrides"] = len(overrides)
        for index, item in enumerate(overrides):
            label = f"{locale_path}: locale_overrides[{index}]"
            override = _require_mapping(item, label, report)
            if override is None:
                continue
            for key in ("locale", "standard_word", "local_word"):
                if not isinstance(override.get(key), str) or not override[key].strip():
                    report.error(f"{label}: {key} must be a non-empty string")
            locale = override.get("locale")
            if locale not in locales:
                report.error(f"{label}: locale {locale!r} is not declared in language.yaml")
        pronunciation = data.get("pronunciation_profiles")
        if pronunciation is not None:
            profiles = (
                _require_list(pronunciation, f"{locale_path}: pronunciation_profiles", report) or []
            )
            for index, item in enumerate(profiles):
                label = f"{locale_path}: pronunciation_profiles[{index}]"
                profile = _require_mapping(item, label, report)
                if profile is None:
                    continue
                if profile.get("locale") not in locales:
                    report.error(
                        f"{label}: locale {profile.get('locale')!r} is not declared "
                        "in language.yaml"
                    )

    if counts["files"] == 0:
        report.error(f"{level_dir}: no grammar, vocabulary, scenario, or locale content files")
    if counts["rules"] == 0 and counts["words"] == 0 and counts["scenarios"] == 0:
        report.warning(f"{level_dir}: level has no grammar, vocabulary, or scenario content")

    return counts


def _is_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    lowered = value.casefold()
    return any(marker in lowered for marker in PLACEHOLDER_MARKERS)


def format_report(report: ValidationReport) -> str:
    lines = [f"Curriculum validation: {report.root}", ""]
    for code, data in report.coverage.items():
        levels = data.get("levels", {})
        lines.append(
            f"{code} — {data.get('name')} [{data.get('level_framework')}] ({data.get('status')})"
        )
        if data.get("features"):
            lines.append(f"  features: {data['features']}")
        for level, counts in levels.items():
            lines.append(
                f"  {level}: {counts['rules']} rules, {counts['words']} words, "
                f"{counts['scenarios']} scenarios, {counts['locale_overrides']} overrides"
            )
        lines.append("")

    if report.warnings:
        lines.append(f"Warnings ({len(report.warnings)}):")
        lines.extend(f"  - {message}" for message in report.warnings)
        lines.append("")
    if report.errors:
        lines.append(f"Errors ({len(report.errors)}):")
        lines.extend(f"  - {message}" for message in report.errors)
        lines.append("")
    lines.append("OK" if report.ok else "FAILED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate Polyglot Coach language packs")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Curriculum directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text")
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors")
    parser.add_argument("--quiet", action="store_true", help="Only print errors")
    args = parser.parse_args(argv)

    report = validate_curriculum(args.root)
    if args.json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "coverage": report.coverage,
                },
                indent=2,
            )
        )
    elif not args.quiet or report.errors:
        print(format_report(report))

    failed = bool(report.errors) or (args.strict and bool(report.warnings))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
