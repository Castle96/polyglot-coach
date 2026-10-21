"""Tests for language metadata, selection validation, and advanced features."""

import pytest
from fastapi import HTTPException

from polyglot_coach_shared.languages import (
    features_for,
    get_feature,
    list_public_languages,
    public_language,
    resolve_selection,
)


def test_public_language_includes_advanced_features():
    language = public_language("es")
    assert language is not None
    assert language["code"] == "es"
    assert language["native_name"] == "Español"
    assert language["level_framework"] == "cefr"
    assert language["levels"] == ["A1"]
    assert language["default_level"] == "A1"
    assert language["default_locale"] == "neutral"
    assert language["script"] == "Latin"
    assert language["direction"] == "ltr"
    assert language["teaching_notes"]
    assert {feature["id"] for feature in language["features"]} >= {
        "ser_estar",
        "gender_agreement",
        "formality",
    }


def test_public_language_locales_are_sorted_with_neutral_first():
    language = public_language("fr")
    assert language is not None
    assert language["locales"][0]["code"] == "neutral"
    assert {locale["code"] for locale in language["locales"]} >= {"fr_FR", "fr_CA"}


def test_list_public_languages_only_returns_enabled_languages():
    codes = [language["code"] for language in list_public_languages()]
    assert codes == ["es", "fr", "de"]
    assert "ja" not in codes


def test_features_for_filters_by_level():
    assert {feature["id"] for feature in features_for("de", "A1")} >= {
        "grammatical_case",
        "word_order",
    }
    assert features_for("de", "B2") == []


def test_get_feature():
    feature = get_feature("fr", "liaison_elision")
    assert feature is not None
    assert feature["category"] == "phonology"
    assert get_feature("fr", "missing_feature") is None


def test_resolve_selection_uses_pack_defaults():
    pack, level, locale = resolve_selection("es")
    assert pack["name"] == "Spanish"
    assert level == "A1"
    assert locale == "neutral"


def test_resolve_selection_accepts_valid_locale_and_feature():
    _, level, locale = resolve_selection("de", locale="de_DE", features=["grammatical_case"])
    assert level == "A1"
    assert locale == "de_DE"


def test_resolve_selection_rejects_unsupported_language():
    with pytest.raises(ValueError, match="Unsupported language 'ja'"):
        resolve_selection("ja")


def test_resolve_selection_rejects_unavailable_level():
    with pytest.raises(ValueError, match="Level 'B2' is not available"):
        resolve_selection("es", level="B2")


def test_resolve_selection_rejects_unknown_locale():
    with pytest.raises(ValueError, match="Locale 'es_AR' is not available"):
        resolve_selection("es", locale="es_AR")


def test_resolve_selection_rejects_feature_not_available_for_language():
    with pytest.raises(ValueError, match="grammatical_case"):
        resolve_selection("es", features=["grammatical_case"])


def test_meta_router_lists_languages():
    from polyglot_coach_api.routers.meta import api_list_languages

    payload = api_list_languages()
    assert [language["code"] for language in payload["languages"]] == ["es", "fr", "de"]


def test_meta_router_language_and_features():
    from polyglot_coach_api.routers.meta import api_get_language, api_get_language_features

    language = api_get_language("de")
    assert language["name"] == "German"

    payload = api_get_language_features("de", level="A1")
    assert payload["language"] == "de"
    assert payload["level"] == "A1"
    assert len(payload["features"]) >= 4


def test_meta_router_missing_language_returns_404():
    from polyglot_coach_api.routers.meta import api_get_language

    with pytest.raises(HTTPException) as exc:
        api_get_language("ja")
    assert exc.value.status_code == 404


def test_meta_router_rejects_unavailable_feature_level():
    from polyglot_coach_api.routers.meta import api_get_language_features

    with pytest.raises(HTTPException) as exc:
        api_get_language_features("es", level="B2")
    assert exc.value.status_code == 422
    assert "Valid levels" in exc.value.detail


def test_tutor_options_rejects_unavailable_level():
    from polyglot_coach_api.routers.tutor import api_tutor_options

    with pytest.raises(HTTPException) as exc:
        api_tutor_options("es", level="C1")
    assert exc.value.status_code == 422


def test_meta_router_lists_frameworks():
    from polyglot_coach_api.routers.meta import api_list_frameworks

    frameworks = {framework["id"] for framework in api_list_frameworks()["frameworks"]}
    assert {"cefr", "jlpt"} <= frameworks
