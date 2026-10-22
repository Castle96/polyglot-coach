"""Tests for OpenAI-compatible and bring-your-own-key LLM providers."""

import io
import json
import urllib.error

import pytest
from fastapi.testclient import TestClient
from polyglot_coach_api.main import app
from polyglot_coach_api.routers import tutor as tutor_router
from polyglot_coach_api.services import llm
from polyglot_coach_api.services.llm import (
    LLMOverrides,
    LLMProviderError,
    OpenAICompatibleConfig,
    TutorResult,
    build_overrides,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset_provider_state(monkeypatch):
    monkeypatch.setattr(llm, "_LLM_BACKEND", None)
    monkeypatch.setattr(llm, "_last_backend_check", 0.0)
    for name in (
        "POLYGLOT_LLM_PROVIDER",
        "POLYGLOT_OPENAI_API_KEY",
        "POLYGLOT_OPENAI_BASE_URL",
        "POLYGLOT_OPENAI_MODEL",
        "POLYGLOT_OPENAI_TIMEOUT",
        "OPENAI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


def _config(**overrides) -> OpenAICompatibleConfig:
    values = {
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-secret",
        "model": "gpt-4o-mini",
    }
    values.update(overrides)
    return OpenAICompatibleConfig(**values)


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = json.dumps(payload).encode()

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_build_overrides_requires_key_with_url_or_model():
    with pytest.raises(ValueError, match="API key is required"):
        build_overrides(base_url="https://api.example.com/v1")
    with pytest.raises(ValueError, match="API key is required"):
        build_overrides(model="some-model")


def test_build_overrides_rejects_invalid_scheme():
    with pytest.raises(ValueError, match="http:// or https://"):
        build_overrides(api_key="sk-test", base_url="ftp://example.com/v1")


def test_build_overrides_rejects_credentials_in_url():
    with pytest.raises(ValueError, match="must not include credentials"):
        build_overrides(api_key="sk-test", base_url="https://user:pass@example.com/v1")


def test_build_overrides_accepts_complete_config():
    overrides = build_overrides(
        api_key="  sk-test  ",
        base_url="https://api.example.com/v1",
        model="example-model",
    )
    assert overrides == LLMOverrides(
        api_key="sk-test",
        base_url="https://api.example.com/v1",
        model="example-model",
    )


def test_chat_completions_url_normalizes_base():
    assert (
        llm._chat_completions_url("https://api.openai.com")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        llm._chat_completions_url("https://api.openai.com/v1/")
        == "https://api.openai.com/v1/chat/completions"
    )
    assert (
        llm._chat_completions_url("https://example.com/v1/chat/completions")
        == "https://example.com/v1/chat/completions"
    )


def test_openai_backend_parses_response(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        captured["body"] = json.loads(req.data)
        captured["timeout"] = timeout
        return _FakeResponse(
            {"choices": [{"message": {"role": "assistant", "content": "Hola, ¿qué tal?"}}]}
        )

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)

    ctx = llm._make_context("es", "A1")[0]
    reply = llm._chat_openai("hola", ctx, {}, [], _config())

    assert reply == "Hola, ¿qué tal?"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["auth"] == "Bearer sk-test-secret"
    assert captured["body"]["model"] == "gpt-4o-mini"
    assert captured["body"]["messages"][-1] == {"role": "user", "content": "hola"}
    assert captured["timeout"] == 90.0


def test_openai_backend_surfaces_http_error(monkeypatch):
    def fake_urlopen(req, timeout):
        raise urllib.error.HTTPError(
            req.full_url,
            401,
            "Unauthorized",
            {},
            io.BytesIO(b'{"error":{"message":"invalid api key sk-test-secret"}}'),
        )

    monkeypatch.setattr(llm.urllib.request, "urlopen", fake_urlopen)

    ctx = llm._make_context("es", "A1")[0]
    with pytest.raises(LLMProviderError) as excinfo:
        llm._chat_openai("hola", ctx, {}, [], _config())

    message = str(excinfo.value)
    assert "HTTP 401" in message
    assert "invalid api key" in message
    assert "[redacted]" in message
    assert "sk-test-secret" not in message


def test_env_provider_is_openai_without_network(monkeypatch):
    monkeypatch.setenv("POLYGLOT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("POLYGLOT_OPENAI_API_KEY", "sk-env-secret")
    monkeypatch.setenv("POLYGLOT_OPENAI_MODEL", "gpt-4o-mini")

    def fail_network(*args, **kwargs):
        raise AssertionError("OpenAI config detection must not make network calls")

    monkeypatch.setattr(llm.urllib.request, "urlopen", fail_network)

    info = llm.provider_info()

    assert info["provider"] == "openai"
    assert info["model"] == "gpt-4o-mini"
    assert "sk-env-secret" not in json.dumps(info)


def test_dedicated_key_enables_openai_in_auto(monkeypatch):
    monkeypatch.setenv("POLYGLOT_OPENAI_API_KEY", "sk-auto")
    monkeypatch.setattr(llm, "_ollama_running", lambda: False)
    monkeypatch.setattr(llm, "_HAS_LLAMA_CPP", False)

    assert llm.provider_info()["provider"] == "openai"


def test_generic_openai_key_does_not_enable_auto(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-unrelated")
    monkeypatch.setattr(llm, "_ollama_running", lambda: False)
    monkeypatch.setattr(llm, "_HAS_LLAMA_CPP", False)

    assert llm.provider_info()["provider"] is None


def test_generic_openai_key_works_for_explicit_provider(monkeypatch):
    monkeypatch.setenv("POLYGLOT_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-explicit")

    assert llm.provider_info()["provider"] == "openai"


def test_byok_headers_are_used_for_chat(monkeypatch):
    captured = {}

    def fake_generate(**kwargs):
        captured["overrides"] = kwargs["overrides"]
        return TutorResult(reply="Bonjour!")

    monkeypatch.setattr(tutor_router, "generate_tutor_response", fake_generate)
    monkeypatch.setattr(tutor_router, "is_llm_available", lambda: False)

    response = client.post(
        "/api/v1/tutor/chat",
        json={"profile_id": 1, "message": "bonjour", "language": "fr"},
        headers={
            "X-Polyglot-LLM-API-Key": "sk-byok",
            "X-Polyglot-LLM-Base-URL": "https://api.example.com/v1",
            "X-Polyglot-LLM-Model": "example-model",
        },
    )

    assert response.status_code == 200
    assert response.json()["reply"] == "Bonjour!"
    assert captured["overrides"] == LLMOverrides(
        api_key="sk-byok",
        base_url="https://api.example.com/v1",
        model="example-model",
    )


def test_byok_without_key_is_rejected():
    response = client.post(
        "/api/v1/tutor/chat",
        json={"profile_id": 1, "message": "hola", "language": "es"},
        headers={"X-Polyglot-LLM-Base-URL": "https://api.example.com/v1"},
    )

    assert response.status_code == 422


def test_byok_provider_error_returns_502(monkeypatch):
    def fail(**kwargs):
        raise LLMProviderError("LLM provider returned HTTP 429: slow down")

    monkeypatch.setattr(tutor_router, "generate_tutor_response", fail)
    monkeypatch.setattr(tutor_router, "is_llm_available", lambda: False)

    response = client.post(
        "/api/v1/tutor/chat",
        json={"profile_id": 1, "message": "hola", "language": "es"},
        headers={"X-Polyglot-LLM-API-Key": "sk-byok"},
    )

    assert response.status_code == 502
    assert "429" in response.json()["detail"]


def test_status_reports_provider_without_key(monkeypatch):
    monkeypatch.setattr(
        tutor_router,
        "provider_info",
        lambda: {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
        },
    )

    response = client.get("/api/v1/tutor/status")

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "openai"
    assert body["byok_supported"] is True
    assert "api_key" not in body


def test_health_reports_provider(monkeypatch):
    monkeypatch.setattr(
        "polyglot_coach_api.main.provider_info",
        lambda: {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1",
        },
    )

    body = client.get("/health").json()

    assert body["llm_provider"] == "openai"
    assert body["llm_available"] is True
