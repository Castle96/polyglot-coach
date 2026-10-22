"""Regression tests for runtime hardening: health probes, limits, and sessions."""

import pytest
from fastapi.testclient import TestClient
from polyglot_coach_api.main import app
from polyglot_coach_api.routers import speech
from polyglot_coach_api.services import llm
from polyglot_coach_shared.database import session_scope
from polyglot_coach_shared.models import LearnerProfile
from sqlalchemy import text

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_llm_cache():
    llm._LLM_BACKEND = None
    llm._last_backend_check = 0.0
    yield
    llm._LLM_BACKEND = None
    llm._last_backend_check = 0.0


def test_health_never_pulls_a_model(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_running", lambda: True)
    monkeypatch.setattr(llm, "_ollama_model_pulled", lambda model: False)

    def fail_pull(model):
        raise AssertionError("health checks must not provision models")

    monkeypatch.setattr(llm, "_ollama_pull", fail_pull)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["llm_available"] is False


def test_readyz_reports_database_and_curriculum(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_running", lambda: False)

    response = client.get("/readyz")

    assert response.status_code == 200
    body = response.json()
    assert body["ready"] is True
    assert body["db_connected"] is True
    assert body["curriculum_loaded"] is True


def test_llm_detection_does_not_pull(monkeypatch):
    monkeypatch.setattr(llm, "_ollama_running", lambda: True)
    monkeypatch.setattr(llm, "_ollama_model_pulled", lambda model: False)

    def fail_pull(model):
        raise AssertionError("detection must not provision models")

    monkeypatch.setattr(llm, "_ollama_pull", fail_pull)

    assert llm.is_llm_available() is False


def test_explicit_provisioning_pulls_missing_model(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "_ollama_running", lambda: True)
    monkeypatch.setattr(llm, "_ollama_model_pulled", lambda model: False)
    monkeypatch.setattr(llm, "_ollama_pull", lambda model: calls.append(model))

    assert llm.ensure_ollama_model() is False
    assert calls == [llm.OLLAMA_MODEL]


def test_chat_rejects_oversized_message():
    response = client.post(
        "/api/v1/tutor/chat",
        json={
            "profile_id": 1,
            "message": "a" * 4001,
            "language": "es",
        },
    )
    assert response.status_code == 422


def test_chat_rejects_oversized_history():
    response = client.post(
        "/api/v1/tutor/chat",
        json={
            "profile_id": 1,
            "message": "hola",
            "language": "es",
            "conversation_history": [{"role": "user", "content": "hola"}] * 21,
        },
    )
    assert response.status_code == 422


def test_chat_rejects_invalid_profile_id():
    response = client.post(
        "/api/v1/tutor/chat",
        json={"profile_id": 0, "message": "hola", "language": "es"},
    )
    assert response.status_code == 422


def test_quick_chat_rejects_oversized_message():
    response = client.get(
        "/api/v1/tutor/quick-chat",
        params={"message": "a" * 4001, "language": "es"},
    )
    assert response.status_code == 422


def test_transcribe_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(speech, "MAX_AUDIO_BYTES", 8)
    monkeypatch.setattr(speech, "is_stt_available", lambda: True)

    response = client.post(
        "/api/v1/speech/transcribe",
        files={"audio": ("sample.wav", b"012345678", "audio/wav")},
        data={"language": "es"},
    )

    assert response.status_code == 413


def test_duplicate_profile_name_returns_conflict():
    first = client.post("/api/v1/learner/profiles", json={"name": "Zoe", "target_language": "es"})
    second = client.post("/api/v1/learner/profiles", json={"name": "Zoe", "target_language": "fr"})

    assert first.status_code == 201
    assert first.json()["id"]
    assert second.status_code == 409


def test_session_scope_commits_on_success(tmp_path):
    db_path = str(tmp_path / "commit.db")
    with session_scope(db_path) as session:
        session.add(
            LearnerProfile(
                name="Commit",
                native_language="en",
                target_language="es",
                locale="neutral",
                proficiency_level="A1",
            )
        )

    with session_scope(db_path) as session:
        assert session.query(LearnerProfile).count() == 1


def test_session_scope_rolls_back_on_error(tmp_path):
    db_path = str(tmp_path / "rollback.db")
    with pytest.raises(RuntimeError), session_scope(db_path) as session:
        session.add(
            LearnerProfile(
                name="Rollback",
                native_language="en",
                target_language="es",
                locale="neutral",
                proficiency_level="A1",
            )
        )
        session.flush()
        raise RuntimeError("boom")

    with session_scope(db_path) as session:
        assert session.query(LearnerProfile).count() == 0


def test_file_database_uses_wal(tmp_path):
    with session_scope(str(tmp_path / "wal.db")) as session:
        assert session.execute(text("PRAGMA journal_mode")).scalar() == "wal"
