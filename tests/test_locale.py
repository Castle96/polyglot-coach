"""Tests for the locale MCP service."""

from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import LocaleOverride


def _seed_overrides():
    session = get_session(":memory:")
    session.add_all([
        LocaleOverride(locale="es_MX", language="es", standard_word="ordenador", local_word="computadora", notes="Mexico"),
        LocaleOverride(locale="es_MX", language="es", standard_word="coche", local_word="carro", notes="Mexico"),
        LocaleOverride(locale="fr_CA", language="fr", standard_word="petit-déjeuner", local_word="déjeuner", notes="Quebec"),
    ])
    session.commit()
    session.close()


def test_get_locale():
    from locale_mcp import get_locale

    _seed_overrides()
    result = get_locale(locale="es_MX", language="es")
    assert result["locale"] == "es_MX"
    assert result["overrides_count"] == 2


def test_get_locale_empty():
    from locale_mcp import get_locale

    result = get_locale(locale="de_DE", language="de")
    assert result["overrides_count"] == 0


def test_vocabulary_overrides():
    from locale_mcp import vocabulary_overrides

    _seed_overrides()
    overrides = vocabulary_overrides(locale="es_MX", language="es")
    assert len(overrides) == 2


def test_vocabulary_overrides_filtered():
    from locale_mcp import vocabulary_overrides

    _seed_overrides()
    overrides = vocabulary_overrides(locale="es_MX", language="es", words=["ordenador"])
    assert len(overrides) == 1
    assert overrides[0]["local_word"] == "computadora"


def test_pronunciation_profile_known():
    from locale_mcp import pronunciation_profile

    profile = pronunciation_profile(locale="es_MX", language="es")
    assert profile["name"] == "Mexican Spanish"
    assert "features" in profile


def test_pronunciation_profile_unknown():
    from locale_mcp import pronunciation_profile

    profile = pronunciation_profile(locale="de_DE", language="de")
    assert "message" in profile
