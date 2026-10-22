"""LLM integration for Polyglot Coach.

Backends, chosen by ``POLYGLOT_LLM_PROVIDER`` (default: ``auto``):
  1. ``openai`` — any OpenAI-compatible chat completions API (OpenAI,
     OpenRouter, Groq, Together, vLLM, LM Studio, Ollama's /v1, …)
  2. ``ollama`` — local Ollama server at OLLAMA_HOST
  3. ``llama-cpp`` — local GGUF via llama-cpp-python

``auto`` prefers an explicitly configured OpenAI-compatible provider
(``POLYGLOT_OPENAI_API_KEY``), then Ollama, then llama-cpp. A bare
``OPENAI_API_KEY`` is only used when ``POLYGLOT_LLM_PROVIDER=openai`` so that an
unrelated key in the environment never causes unexpected cloud usage.

Users can also bring their own key per request: the web client sends
``X-Polyglot-LLM-API-Key``, ``X-Polyglot-LLM-Base-URL``, and
``X-Polyglot-LLM-Model`` headers, which override the server configuration.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from polyglot_coach_api.services.prompts import _MODE_ALIAS, TutorContext, build_tutor_prompt
from polyglot_coach_shared.database import session_scope
from polyglot_coach_shared.languages import (
    features_for,
    get_language,
    language_name,
    level_framework,
)
from polyglot_coach_shared.models import (
    GrammarRule,
    LearnerProfile,
    MistakeRecord,
    ProgressRecord,
    VocabularyEntry,
)

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
GGUF_PATH = os.environ.get("POLYGLOT_LLM_MODEL_PATH", "")

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_TIMEOUT = 90.0
MAX_API_KEY_LENGTH = 500
MAX_BASE_URL_LENGTH = 500
MAX_MODEL_LENGTH = 200
VALID_PROVIDERS = {"auto", "openai", "ollama", "llama-cpp"}

_HAS_LLAMA_CPP = False
try:
    import llama_cpp  # noqa: F401

    _HAS_LLAMA_CPP = True
except ImportError:
    pass


@dataclass
class ParsedCorrection:
    correction: str = ""
    why: str = ""
    alternative: str = ""


@dataclass
class TutorResult:
    reply: str
    corrections: list[ParsedCorrection] = field(default_factory=list)


class LLMProviderError(RuntimeError):
    """A configured LLM provider could not produce a response."""


@dataclass(frozen=True)
class OpenAICompatibleConfig:
    base_url: str
    api_key: str
    model: str
    timeout: float = DEFAULT_OPENAI_TIMEOUT


@dataclass(frozen=True)
class LLMOverrides:
    """Per-request provider settings supplied by a client (bring your own key)."""

    api_key: str = ""
    base_url: str | None = None
    model: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.api_key)


def build_overrides(
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> LLMOverrides | None:
    """Validate and normalize optional per-request provider headers."""
    api_key = (api_key or "").strip()
    base_url = (base_url or "").strip() or None
    model = (model or "").strip() or None

    if not api_key:
        if base_url or model:
            raise ValueError("An API key is required when setting a provider URL or model.")
        return None

    if len(api_key) > MAX_API_KEY_LENGTH:
        raise ValueError(f"API key exceeds {MAX_API_KEY_LENGTH} characters.")
    if base_url:
        if len(base_url) > MAX_BASE_URL_LENGTH:
            raise ValueError(f"Base URL exceeds {MAX_BASE_URL_LENGTH} characters.")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Base URL must be an http:// or https:// URL.")
        if parsed.username or parsed.password:
            raise ValueError("Base URL must not include credentials; use the API key field.")
    if model and len(model) > MAX_MODEL_LENGTH:
        raise ValueError(f"Model name exceeds {MAX_MODEL_LENGTH} characters.")

    return LLMOverrides(api_key=api_key, base_url=base_url, model=model)


def _configured_provider() -> str:
    provider = os.environ.get("POLYGLOT_LLM_PROVIDER", "auto").strip().lower()
    if provider not in VALID_PROVIDERS:
        logger.warning(
            "Unknown POLYGLOT_LLM_PROVIDER=%r; falling back to 'auto'. Valid values: %s",
            provider,
            ", ".join(sorted(VALID_PROVIDERS)),
        )
        return "auto"
    return provider


def _env_openai_config() -> OpenAICompatibleConfig | None:
    provider = _configured_provider()
    if provider not in {"auto", "openai"}:
        return None

    api_key = os.environ.get("POLYGLOT_OPENAI_API_KEY", "").strip()
    if not api_key and provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    base_url = os.environ.get("POLYGLOT_OPENAI_BASE_URL", "").strip() or DEFAULT_OPENAI_BASE_URL
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username
        or parsed.password
    ):
        logger.warning(
            "POLYGLOT_OPENAI_BASE_URL=%r is not a valid http(s) URL without credentials; "
            "provider disabled",
            base_url,
        )
        return None

    model = os.environ.get("POLYGLOT_OPENAI_MODEL", "").strip() or DEFAULT_OPENAI_MODEL
    try:
        timeout = float(os.environ.get("POLYGLOT_OPENAI_TIMEOUT", DEFAULT_OPENAI_TIMEOUT))
    except ValueError:
        timeout = DEFAULT_OPENAI_TIMEOUT
    if not 1.0 <= timeout <= 600.0:
        timeout = DEFAULT_OPENAI_TIMEOUT
    return OpenAICompatibleConfig(
        base_url=base_url.rstrip("/"),
        api_key=api_key,
        model=model,
        timeout=timeout,
    )


def _resolve_openai_config(
    overrides: LLMOverrides | None = None,
) -> OpenAICompatibleConfig | None:
    if overrides and overrides.enabled:
        env = _env_openai_config()
        return OpenAICompatibleConfig(
            base_url=(
                overrides.base_url or (env.base_url if env else None) or DEFAULT_OPENAI_BASE_URL
            ).rstrip("/"),
            api_key=overrides.api_key,
            model=overrides.model or (env.model if env else None) or DEFAULT_OPENAI_MODEL,
            timeout=env.timeout if env else DEFAULT_OPENAI_TIMEOUT,
        )
    return _env_openai_config()


def provider_info() -> dict[str, str | None]:
    """Describe the active server-level provider without exposing credentials."""
    backend = _detect_backend()
    if backend == "openai":
        config = _env_openai_config()
        return {
            "provider": "openai",
            "model": config.model if config else None,
            "base_url": config.base_url if config else None,
        }
    if backend == "ollama":
        return {"provider": "ollama", "model": OLLAMA_MODEL, "base_url": OLLAMA_HOST}
    if backend == "llama-cpp":
        return {
            "provider": "llama-cpp",
            "model": Path(GGUF_PATH).name if GGUF_PATH else None,
            "base_url": None,
        }
    return {"provider": None, "model": None, "base_url": None}


# ---------------------------------------------------------------------------
# Correction parsing
# ---------------------------------------------------------------------------

_CORRECTION_RE = re.compile(
    r"Correction:\s*\n(.+?)\n\s*Why:\s*\n(.+?)(?:\n\s*Alternative:\s*\n(.+?))?(?:\n|$)",
    re.DOTALL,
)


def _parse_corrections(response: str) -> tuple[str, list[ParsedCorrection]]:
    match = _CORRECTION_RE.search(response)
    if not match:
        return response.strip(), []

    main = response[: match.start()].strip()
    parsed = ParsedCorrection(
        correction=match.group(1).strip(),
        why=match.group(2).strip(),
        alternative=match.group(3).strip() if match.group(3) else "",
    )
    return main, [parsed]


# ---------------------------------------------------------------------------
# Learner context enrichment
# ---------------------------------------------------------------------------


def _enrich_from_profile(profile_id: int | None, ctx: TutorContext) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if profile_id is None:
        return extra

    try:
        with session_scope() as session:
            profile = session.query(LearnerProfile).filter(LearnerProfile.id == profile_id).first()
            if profile is None:
                return extra

            ctx.learner_name = profile.name
            ctx.native_language = profile.native_language
            # Level and locale come from the validated session request. The profile
            # supplies defaults to the UI, but must not silently override selectors.

            vocab_count = (
                session.query(VocabularyEntry)
                .filter(
                    VocabularyEntry.profile_id == profile_id,
                )
                .count()
            )
            if vocab_count:
                extra["vocabulary_count"] = vocab_count

            recent_mistakes = (
                session.query(MistakeRecord)
                .filter(MistakeRecord.profile_id == profile_id)
                .order_by(MistakeRecord.created_at.desc())
                .limit(5)
                .all()
            )
            if recent_mistakes:
                extra["recent_mistakes"] = [
                    {"category": m.category, "correction": m.correction} for m in recent_mistakes
                ]
    except Exception:
        logger.warning("Could not enrich tutor context from profile %s", profile_id, exc_info=True)

    return extra


def _enrich_due_words(profile_id: int | None, language: str, extra: dict[str, Any]) -> None:
    if profile_id is None:
        return
    try:
        from review import get_due_words

        due = get_due_words(profile_id=profile_id, limit=10)
        if due:
            extra["due_words"] = due
    except Exception:
        logger.warning("Could not load due review words for profile %s", profile_id, exc_info=True)


def _enrich_curriculum(language: str, level: str, extra: dict[str, Any]) -> None:
    try:
        with session_scope() as session:
            rules = (
                session.query(GrammarRule)
                .filter(GrammarRule.language == language, GrammarRule.level == level)
                .limit(5)
                .all()
            )
            if rules:
                extra["grammar_rules"] = [{"title": r.title, "category": r.category} for r in rules]

            vocab = (
                session.query(VocabularyEntry)
                .filter(VocabularyEntry.language == language, VocabularyEntry.profile_id == 0)
                .limit(10)
                .all()
            )
            if vocab:
                extra["curriculum_vocab"] = [{"word": v.word, "tags": v.tags or ""} for v in vocab]
    except Exception:
        logger.warning("Could not enrich tutor context from curriculum", exc_info=True)


# ---------------------------------------------------------------------------
# Progress & mistake recording
# ---------------------------------------------------------------------------


def _store_corrections(
    profile_id: int | None,
    user_message: str,
    corrections: list[ParsedCorrection],
    ctx: TutorContext,
) -> None:
    if not profile_id or not corrections:
        return
    try:
        from learner_memory import record_mistake

        for c in corrections:
            record_mistake(
                profile_id=profile_id,
                category="grammar",
                user_input=user_message,
                correction=c.correction,
                explanation=c.why if c.why else None,
                context=f"{ctx.mode} session — {ctx.language} {ctx.level}",
            )
    except Exception:
        logger.warning("Could not record corrections for profile %s", profile_id, exc_info=True)


def _record_progress(
    profile_id: int | None,
    event_type: str,
    detail: str | None = None,
    score: float | None = None,
) -> None:
    if profile_id is None:
        return
    try:
        with session_scope() as session:
            session.add(
                ProgressRecord(
                    profile_id=profile_id,
                    event_type=event_type,
                    detail=detail,
                    score=score,
                )
            )
    except Exception:
        logger.warning("Could not record progress for profile %s", profile_id, exc_info=True)


def _schedule_vocab_review(
    profile_id: int | None, corrections: list[ParsedCorrection], language: str
) -> None:
    if not profile_id or not corrections:
        return
    try:
        from review import schedule_review

        for c in corrections:
            word = c.correction.split()[0] if c.correction else ""
            word = word.strip(".,!?;:\"'")
            if word and len(word) > 1:
                schedule_review(profile_id=profile_id, word=word, language=language)
    except Exception:
        logger.warning(
            "Could not schedule vocabulary review for profile %s", profile_id, exc_info=True
        )


# ---------------------------------------------------------------------------
# Ollama helpers
# ---------------------------------------------------------------------------


def _ollama_running() -> bool:
    try:
        urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=2)
        return True
    except Exception:
        return False


def _ollama_model_pulled(model: str) -> bool:
    try:
        req = urllib.request.Request(f"{OLLAMA_HOST}/api/tags")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read())
        return any(m["name"].startswith(model) for m in data.get("models", []))
    except Exception:
        return False


def _ollama_pull(model: str) -> None:
    print(f"Ollama: pulling {model} (this may take a while)...")
    body = json.dumps({"name": model}).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/pull",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=3600)
    for line in resp:
        try:
            msg = json.loads(line)
            if "status" in msg:
                print(f"  {msg['status']}")
        except json.JSONDecodeError:
            pass
    print("  Done.")


# ---------------------------------------------------------------------------
# Backend detection
# ---------------------------------------------------------------------------

_LLM_BACKEND: str | None = None
_llama_model = None
_BACKEND_CHECK_INTERVAL = 10.0
_last_backend_check = 0.0


def _detect_backend(force: bool = False) -> str | None:
    """Return the active LLM backend without provisioning anything.

    Detection is intentionally cheap: it never downloads a model. Pulling is an
    explicit operation via :func:`ensure_ollama_model` or the CLI/run script, so
    health checks and requests can never trigger a multi-gigabyte download.
    """
    global _LLM_BACKEND, _last_backend_check
    if _LLM_BACKEND:
        return _LLM_BACKEND

    now = time.monotonic()
    if not force and now - _last_backend_check < _BACKEND_CHECK_INTERVAL:
        return None
    _last_backend_check = now

    provider = _configured_provider()

    if provider in {"auto", "openai"}:
        if _env_openai_config() is not None:
            _LLM_BACKEND = "openai"
            return _LLM_BACKEND
        if provider == "openai":
            logger.warning(
                "POLYGLOT_LLM_PROVIDER=openai requires POLYGLOT_OPENAI_API_KEY "
                "(or OPENAI_API_KEY); no provider is configured."
            )
            return None

    if provider in {"auto", "ollama"} and _ollama_running():
        if _ollama_model_pulled(OLLAMA_MODEL):
            _LLM_BACKEND = "ollama"
            return _LLM_BACKEND
        logger.warning(
            "Ollama is running but model %s is not pulled; run `ollama pull %s`",
            OLLAMA_MODEL,
            OLLAMA_MODEL,
        )

    if provider in {"auto", "llama-cpp"}:
        if _HAS_LLAMA_CPP and GGUF_PATH and Path(GGUF_PATH).exists():
            _LLM_BACKEND = "llama-cpp"
            return _LLM_BACKEND

    return None


def is_llm_available() -> bool:
    return _detect_backend() is not None


def ensure_ollama_model() -> bool:
    """Pull the configured Ollama model if Ollama is reachable.

    This is provisioning, not detection. Never call it from a request path.
    """
    if not _ollama_running():
        return False
    if _ollama_model_pulled(OLLAMA_MODEL):
        return True
    _ollama_pull(OLLAMA_MODEL)
    return _ollama_model_pulled(OLLAMA_MODEL)


def load_model():
    global _llama_model
    backend = _detect_backend()
    if backend == "llama-cpp" and _llama_model is None:
        from llama_cpp import Llama

        _llama_model = Llama(model_path=GGUF_PATH, n_ctx=4096, verbose=False)
    return _llama_model


# ---------------------------------------------------------------------------
# Chat completion
# ---------------------------------------------------------------------------


def _resolve_language_name(code: str) -> str:
    """Resolve a target-language code from the curriculum registry.

    Unknown codes intentionally fall back to the code itself rather than a
    hardcoded list, so adding a language does not require editing this module.
    """
    return language_name(code)


def _make_context(
    language: str,
    level: str,
    profile_id: int | None = None,
    mode: str = "conversation",
    learner_name: str = "Learner",
    native_language: str = "en",
    locale: str = "neutral",
    grammar_focus: list[str] | None = None,
    scenario_context: str | None = None,
    vocabulary_hints: list[str] | None = None,
    feature_focus: list[str] | None = None,
) -> tuple[TutorContext, dict[str, Any]]:
    lang_name = _resolve_language_name(language)
    mode_normalized = _normalize_mode(mode)
    ctx = TutorContext(
        language=lang_name,
        language_code=language,
        level=level,
        native_language=native_language,
        locale=locale,
        mode=mode_normalized,
        learner_name=learner_name,
        profile_id=profile_id,
        grammar_focus=grammar_focus,
        scenario_context=scenario_context,
        vocabulary_hints=vocabulary_hints,
        feature_focus=feature_focus,
    )
    extra = _enrich_from_profile(profile_id, ctx)

    pack = get_language(language) or {}
    available_features = features_for(language, ctx.level)
    available_ids = {feature.get("id") for feature in available_features}
    ctx.language_features = available_features
    ctx.teaching_notes = list(pack.get("teaching_notes", []))
    ctx.script = pack.get("script")
    ctx.direction = pack.get("direction", "ltr")
    framework = level_framework(language) or {}
    ctx.proficiency_framework = framework.get("name")
    ctx.feature_focus = [
        feature for feature in (feature_focus or []) if feature in available_ids
    ] or None

    _enrich_due_words(profile_id, language, extra)
    _enrich_curriculum(language, ctx.level, extra)
    return ctx, extra


def _normalize_mode(mode: str) -> str:
    mode_lower = mode.lower()
    if mode_lower in _MODE_ALIAS:
        return _MODE_ALIAS[mode_lower]
    return "conversation"


def _build_messages(system: str, history: list[dict], message: str) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = [{"role": "system", "content": system}]
    for h in history[-8:]:
        role = "user" if h.get("role") == "user" else "assistant"
        messages.append({"role": role, "content": h.get("content", "")})
    messages.append({"role": "user", "content": message})
    return messages


def _chat_completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/chat/completions"):
        return base
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/chat/completions"


def _redact_secret(text: str, secret: str) -> str:
    """Keep provider responses from echoing a credential back to the client."""
    if secret:
        return text.replace(secret, "[redacted]")
    return text


def _provider_error_detail(exc: urllib.error.HTTPError) -> str:
    try:
        raw = exc.read(1000).decode("utf-8", "replace").strip()
    except Exception:
        return str(exc.reason or "no response body")
    if not raw:
        return str(exc.reason or "no response body")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw[:300]
    error = data.get("error") if isinstance(data, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error)[:300]
    if error:
        return str(error)[:300]
    message = data.get("message") if isinstance(data, dict) else None
    return str(message or raw)[:300]


def _chat_openai(
    message: str,
    ctx: TutorContext,
    extra: dict[str, Any],
    history: list[dict],
    config: OpenAICompatibleConfig,
) -> str:
    system = build_tutor_prompt(ctx, history, extra)
    messages = _build_messages(system, history, message)
    body = json.dumps(
        {
            "model": config.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 512,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        _chat_completions_url(config.base_url),
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {config.api_key}",
            "User-Agent": "polyglot-coach/0.1",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=config.timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as exc:
        detail = _redact_secret(_provider_error_detail(exc), config.api_key)
        raise LLMProviderError(f"LLM provider returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        detail = _redact_secret(str(exc.reason), config.api_key)
        raise LLMProviderError(
            f"Could not reach LLM provider at {config.base_url}: {detail}"
        ) from exc
    except TimeoutError as exc:
        raise LLMProviderError("The LLM provider timed out.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise LLMProviderError("The LLM provider returned invalid JSON.") from exc

    choices = data.get("choices") or []
    if not choices:
        raise LLMProviderError("The LLM provider returned no choices.")
    content = (choices[0].get("message") or {}).get("content")
    if isinstance(content, list):
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError("The LLM provider returned an empty response.")
    return content.strip()


def _chat_ollama(
    message: str,
    ctx: TutorContext,
    extra: dict[str, Any],
    history: list[dict],
) -> str:
    system = build_tutor_prompt(ctx, history, extra)
    messages = _build_messages(system, history, message)

    body = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 512},
        }
    ).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data.get("message", {}).get("content", "").strip()


def _chat_llamacpp(
    message: str,
    ctx: TutorContext,
    extra: dict[str, Any],
    history: list[dict],
) -> str:
    model = load_model()
    if model is None:
        return _fallback_response(ctx)

    system = build_tutor_prompt(ctx, history, extra)
    prompt = f"<|system|>\n{system}\n<|user|>\n{message}\n<|assistant|>\n"

    response = model(prompt, max_tokens=512, temperature=0.7, stop=["<|user|>", "<|system|>"])
    return response["choices"][0]["text"].strip() if response.get("choices") else ""


def generate_tutor_response(
    message: str,
    language: str,
    level: str,
    history: list[dict],
    profile_id: int | None = None,
    mode: str = "conversation",
    learner_name: str = "Learner",
    native_language: str = "en",
    locale: str = "neutral",
    grammar_focus: list[str] | None = None,
    scenario_context: str | None = None,
    vocabulary_hints: list[str] | None = None,
    feature_focus: list[str] | None = None,
    overrides: LLMOverrides | None = None,
) -> TutorResult:
    ctx, extra = _make_context(
        language=language,
        level=level,
        profile_id=profile_id,
        mode=mode,
        learner_name=learner_name,
        native_language=native_language,
        locale=locale,
        grammar_focus=grammar_focus,
        scenario_context=scenario_context,
        vocabulary_hints=vocabulary_hints,
        feature_focus=feature_focus,
    )

    backend = "openai" if (overrides and overrides.enabled) else _detect_backend()
    try:
        if backend == "openai":
            config = _resolve_openai_config(overrides)
            if config is None:
                raise LLMProviderError("No OpenAI-compatible provider is configured.")
            raw = _chat_openai(message, ctx, extra, history, config)
        elif backend == "ollama":
            raw = _chat_ollama(message, ctx, extra, history)
        elif backend == "llama-cpp":
            raw = _chat_llamacpp(message, ctx, extra, history)
        else:
            raw = _fallback_response(ctx)
    except LLMProviderError:
        raise
    except Exception:
        logger.exception("LLM backend %r failed; returning fallback response", backend)
        raw = _fallback_response(ctx)

    reply, corrections = _parse_corrections(raw)

    if corrections:
        _store_corrections(profile_id, message, corrections, ctx)
        _schedule_vocab_review(profile_id, corrections, language)

    _record_progress(
        profile_id,
        event_type="chat",
        detail=f"{ctx.mode} — {language} {ctx.level}",
    )

    return TutorResult(reply=reply, corrections=corrections)


def _fallback_response(ctx: TutorContext) -> str:
    return (
        f"As your {ctx.language} tutor at {ctx.level} level, "
        "I would suggest practicing with more example sentences. "
        "(No LLM backend available — install Ollama or set POLYGLOT_LLM_MODEL_PATH)"
    )
