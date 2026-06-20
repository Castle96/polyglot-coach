"""Pytest configuration — sets in-memory database for all tests."""

import os

import pytest

from polyglot_coach_shared.database import _engine_cache

os.environ["POLYGLOT_DB_PATH"] = ":memory:"


@pytest.fixture(autouse=True)
def _fresh_database():
    """Clear engine cache before each test so every test gets a fresh in-memory DB."""
    _engine_cache.clear()
    yield
    _engine_cache.clear()
