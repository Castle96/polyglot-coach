"""LLM integration for Polyglot Coach.

Supports two backends, checked in order:
  1. Ollama (recommended) — talks to local Ollama server at OLLAMA_HOST
  2. llama-cpp-python — loads a GGUF file from POLYGLOT_LLM_MODEL_PATH

Set OLLAMA_MODEL (default: qwen2.5:7b) to choose the model pulled by Ollama.
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from polyglot_coach_api.services.prompts import _MODE_ALIAS, TutorContext, build_tutor_prompt
from polyglot_coach_shared.database import get_session
from polyglot_coach_shared.models import GrammarRule, LearnerProfile, MistakeRecord, ProgressRecord, VocabularyEntry

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
GGUF_PATH = os.environ.get("POLYGLOT_LLM_MODEL_PATH", "")

_LANGUAGE_MAP = {
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "ja": "Japanese",
    "en": "English",
    "pt": "Portuguese",
    "it": "Italian",
    "zh": "Chinese",
    "ko": "Korean",
    "ru": "Russian",
}

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
        session = get_session()

        profile = session.query(LearnerProfile).filter(LearnerProfile.id == profile_id).first()
        if profile is None:
            session.close()
            return extra

        ctx.learner_name = profile.name
        ctx.native_language = profile.native_language
        ctx.locale = profile.locale or "neutral"
        ctx.level = profile.proficiency_level or ctx.level

        vocab_count = session.query(VocabularyEntry).filter(
            VocabularyEntry.profile_id == profile_id,
        ).count()
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

        session.close()
    except Exception:
        pass

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
        pass


def _enrich_curriculum(language: str, level: str, extra: dict[str, Any]) -> None:
    try:
        session = get_session()

        rules = (
            session.query(GrammarRule)
            .filter(GrammarRule.language == language, GrammarRule.level == level)
            .limit(5)
            .all()
        )
        if rules:
            extra["grammar_rules"] = [
                {"title": r.title, "category": r.category} for r in rules
            ]

        vocab = (
            session.query(VocabularyEntry)
            .filter(VocabularyEntry.language == language, VocabularyEntry.profile_id == 0)
            .limit(10)
            .all()
        )
        if vocab:
            extra["curriculum_vocab"] = [
                {"word": v.word, "tags": v.tags or ""} for v in vocab
            ]

        session.close()
    except Exception:
        pass


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
        pass


def _record_progress(
    profile_id: int | None,
    event_type: str,
    detail: str | None = None,
    score: float | None = None,
) -> None:
    if profile_id is None:
        return
    try:
        session = get_session()
        record = ProgressRecord(
            profile_id=profile_id,
            event_type=event_type,
            detail=detail,
            score=score,
        )
        session.add(record)
        session.commit()
        session.close()
    except Exception:
        pass


def _schedule_vocab_review(profile_id: int | None, corrections: list[ParsedCorrection], language: str) -> None:
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
        pass


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


def _detect_backend() -> str | None:
    global _LLM_BACKEND
    if _LLM_BACKEND:
        return _LLM_BACKEND

    if _ollama_running():
        model = OLLAMA_MODEL
        if not _ollama_model_pulled(model):
            _ollama_pull(model)
        _LLM_BACKEND = "ollama"
        return _LLM_BACKEND

    if _HAS_LLAMA_CPP and GGUF_PATH and Path(GGUF_PATH).exists():
        _LLM_BACKEND = "llama-cpp"
        return _LLM_BACKEND

    return None


def is_llm_available() -> bool:
    return _detect_backend() is not None


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
    return _LANGUAGE_MAP.get(code, code)


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
    )
    extra = _enrich_from_profile(profile_id, ctx)
    _enrich_due_words(profile_id, language, extra)
    _enrich_curriculum(language, level, extra)
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


def _chat_ollama(
    message: str,
    ctx: TutorContext,
    extra: dict[str, Any],
    history: list[dict],
) -> str:
    system = build_tutor_prompt(ctx, history, extra)
    messages = _build_messages(system, history, message)

    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512},
    }).encode()
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
    )

    backend = _detect_backend()
    if backend == "ollama":
        raw = _chat_ollama(message, ctx, extra, history)
    elif backend == "llama-cpp":
        raw = _chat_llamacpp(message, ctx, extra, history)
    else:
        raw = _fallback_response(ctx)

    reply, corrections = _parse_corrections(raw)

    if corrections:
        _store_corrections(profile_id, message, corrections, ctx)
        _schedule_vocab_review(profile_id, corrections, language)

    _record_progress(
        profile_id,
        event_type="chat",
        detail=f"{ctx.mode} — {language} {level}",
    )

    return TutorResult(reply=reply, corrections=corrections)


def _fallback_response(ctx: TutorContext) -> str:
    return (
        f"As your {ctx.language} tutor at {ctx.level} level, "
        "I would suggest practicing with more example sentences. "
        "(No LLM backend available — install Ollama or set POLYGLOT_LLM_MODEL_PATH)"
    )
