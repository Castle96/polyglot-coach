"""Tests for learner-profile language selection validation."""

import pytest
from fastapi import HTTPException
from polyglot_coach_api.routers.learner import (
    ProfileCreate,
    ProfileUpdate,
    api_create_profile,
    api_update_profile,
)


def test_create_profile_applies_pack_defaults():
    profile = api_create_profile(ProfileCreate(name="Ana", target_language="es"))
    assert profile["proficiency_level"] == "A1"
    assert profile["locale"] == "neutral"


def test_create_profile_accepts_declared_locale():
    profile = api_create_profile(ProfileCreate(name="Ben", target_language="fr", locale="fr_CA"))
    assert profile["proficiency_level"] == "A1"
    assert profile["locale"] == "fr_CA"


def test_create_profile_rejects_invalid_level():
    with pytest.raises(HTTPException) as exc:
        api_create_profile(ProfileCreate(name="Cara", target_language="de", proficiency_level="B1"))
    assert exc.value.status_code == 422
    assert "Valid levels" in exc.value.detail


def test_create_profile_rejects_unsupported_language():
    with pytest.raises(HTTPException) as exc:
        api_create_profile(ProfileCreate(name="Dai", target_language="ja"))
    assert exc.value.status_code == 422


def test_update_profile_validates_existing_selection():
    profile = api_create_profile(ProfileCreate(name="Eve", target_language="es"))

    updated = api_update_profile(profile["id"], ProfileUpdate(locale="es_MX"))
    assert updated is not None
    assert updated["locale"] == "es_MX"

    with pytest.raises(HTTPException) as exc:
        api_update_profile(profile["id"], ProfileUpdate(target_language="ja"))
    assert exc.value.status_code == 422


def test_update_profile_rejects_invalid_locale():
    profile = api_create_profile(ProfileCreate(name="Finn", target_language="de"))

    with pytest.raises(HTTPException) as exc:
        api_update_profile(profile["id"], ProfileUpdate(locale="de_AT"))
    assert exc.value.status_code == 422
    assert "Valid locales" in exc.value.detail
