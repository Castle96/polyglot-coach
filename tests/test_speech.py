"""Tests for the local speech API endpoints."""

from fastapi.testclient import TestClient

from polyglot_coach_api.main import app
from polyglot_coach_api.routers import speech


def test_speech_status(monkeypatch):
    monkeypatch.setattr(speech, "is_stt_available", lambda: False)
    monkeypatch.setattr(speech, "is_tts_available", lambda: True)

    response = TestClient(app).get("/api/v1/speech/status")

    assert response.status_code == 200
    assert response.json()["stt_available"] is False
    assert response.json()["tts_available"] is True
    assert response.json()["stt_model"]


def test_transcribe_uses_locale_stt_language(monkeypatch):
    monkeypatch.setattr(speech, "is_stt_available", lambda: True)

    captured = {}

    def fake_transcribe(data, language=None, suffix=".wav"):
        captured.update({"data": data, "language": language, "suffix": suffix})
        return {"text": "Hola, ¿cómo estás?", "language": "es", "duration": 1.2}

    monkeypatch.setattr(speech, "transcribe", fake_transcribe)

    response = TestClient(app).post(
        "/api/v1/speech/transcribe",
        files={"audio": ("sample.webm", b"fake-audio", "audio/webm")},
        data={"language": "es", "level": "A1", "locale": "es_MX"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Hola, ¿cómo estás?"
    assert response.json()["level"] == "A1"
    assert response.json()["locale"] == "es_MX"
    assert captured == {"data": b"fake-audio", "language": "es", "suffix": ".webm"}


def test_transcribe_rejects_invalid_selection_before_model_check(monkeypatch):
    monkeypatch.setattr(
        speech,
        "is_stt_available",
        lambda: (_ for _ in ()).throw(AssertionError("availability should not be checked")),
    )

    response = TestClient(app).post(
        "/api/v1/speech/transcribe",
        files={"audio": ("sample.wav", b"fake-audio", "audio/wav")},
        data={"language": "es", "level": "C1"},
    )

    assert response.status_code == 422
    assert "Valid levels" in response.json()["detail"]


def test_transcribe_reports_missing_stt(monkeypatch):
    monkeypatch.setattr(speech, "is_stt_available", lambda: False)

    response = TestClient(app).post(
        "/api/v1/speech/transcribe",
        files={"audio": ("sample.wav", b"fake-audio", "audio/wav")},
        data={"language": "fr"},
    )

    assert response.status_code == 503
    assert "speech" in response.json()["detail"].lower()


def test_synthesize_returns_wav(monkeypatch):
    monkeypatch.setattr(speech, "is_tts_available", lambda: True)
    captured = {}

    def fake_synthesize(text, locale="neutral", language=None):
        captured.update({"text": text, "locale": locale, "language": language})
        return b"RIFFfakewav"

    monkeypatch.setattr(speech, "synthesize", fake_synthesize)

    response = TestClient(app).post(
        "/api/v1/speech/synthesize",
        json={"text": "Bonjour", "language": "fr", "level": "A1", "locale": "fr_CA"},
    )

    assert response.status_code == 200
    assert response.content == b"RIFFfakewav"
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["x-polyglot-locale"] == "fr_CA"
    assert captured == {"text": "Bonjour", "locale": "fr", "language": "fr"}


def test_synthesize_reports_missing_voice(monkeypatch):
    monkeypatch.setattr(speech, "is_tts_available", lambda: True)
    monkeypatch.setattr(speech, "synthesize", lambda *args, **kwargs: None)

    response = TestClient(app).post(
        "/api/v1/speech/synthesize",
        json={"text": "Hallo", "language": "de"},
    )

    assert response.status_code == 503
    assert "No Piper voice" in response.json()["detail"]


def test_synthesize_rejects_invalid_locale(monkeypatch):
    monkeypatch.setattr(
        speech,
        "is_tts_available",
        lambda: (_ for _ in ()).throw(AssertionError("availability should not be checked")),
    )

    response = TestClient(app).post(
        "/api/v1/speech/synthesize",
        json={"text": "Hallo", "language": "de", "locale": "de_AT"},
    )

    assert response.status_code == 422
    assert "Valid locales" in response.json()["detail"]
