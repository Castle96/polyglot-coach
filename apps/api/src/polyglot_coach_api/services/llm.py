"""LLM integration for Polyglot Coach.

Supports two backends, checked in order:
  1. Ollama (recommended) — talks to local Ollama server at OLLAMA_HOST
  2. llama-cpp-python — loads a GGUF file from POLYGLOT_LLM_MODEL_PATH

Set OLLAMA_MODEL (default: qwen2.5:7b) to choose the model pulled by Ollama.
"""

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
GGUF_PATH = os.environ.get("POLYGLOT_LLM_MODEL_PATH", "")

_HAS_LLAMA_CPP = False
try:
    import llama_cpp  # noqa: F401 — check availability

    _HAS_LLAMA_CPP = True
except ImportError:
    pass

TUTOR_SYSTEM_PROMPT = """You are Polyglot Coach, an AI language tutor. Your role:
- Teach {language} at CEFR level {level}
- Respond primarily in the target language with English explanations when needed
- Correct mistakes gently and explain grammar in context
- Adapt vocabulary to the learner's level
- Keep responses concise (2-4 sentences in the target language, then 1-2 in English if needed)
- Never translate everything — encourage immersion

Current conversation context:
{history}

Respond as a helpful, patient tutor."""


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
        f"{OLLAMA_HOST}/api/pull", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    # Stream response (Ollama sends progress lines)
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

_LLM_BACKEND: str | None = None  # "ollama" | "llama-cpp" | None
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
    return _llama_model  # only used by llama-cpp backend


# ---------------------------------------------------------------------------
# Chat completion
# ---------------------------------------------------------------------------

def _chat_ollama(message: str, language: str, level: str, history: list[dict]) -> str:
    history_text = "\n".join(
        f"{'Learner' if h.get('role') == 'user' else 'Tutor'}: {h.get('content', '')}"
        for h in history[-6:]
    )
    system = TUTOR_SYSTEM_PROMPT.format(language=language, level=level, history=history_text)

    messages = [{"role": "system", "content": system}]
    messages.extend(history[-6:])
    messages.append({"role": "user", "content": message})

    body = json.dumps({
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.7, "num_predict": 512},
    }).encode()
    req = urllib.request.Request(
        f"{OLLAMA_HOST}/api/chat", data=body, method="POST",
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=120)
    data = json.loads(resp.read())
    return data.get("message", {}).get("content", "").strip()


def _chat_llamacpp(message: str, language: str, level: str, history: list[dict]) -> str:
    model = load_model()
    if model is None:
        return _fallback_response(message, language, level)

    history_text = "\n".join(
        f"{'Learner' if h.get('role') == 'user' else 'Tutor'}: {h.get('content', '')}"
        for h in history[-6:]
    )
    system = TUTOR_SYSTEM_PROMPT.format(language=language, level=level, history=history_text)
    prompt = f"<|system|>\n{system}\n<|user|>\n{message}\n<|assistant|>\n"

    response = model(prompt, max_tokens=512, temperature=0.7, stop=["<|user|>", "<|system|>"])
    return response["choices"][0]["text"].strip() if response.get("choices") else ""


def generate_tutor_response(message: str, language: str, level: str, history: list[dict]) -> str:
    backend = _detect_backend()
    if backend == "ollama":
        return _chat_ollama(message, language, level, history)
    if backend == "llama-cpp":
        return _chat_llamacpp(message, language, level, history)
    return _fallback_response(message, language, level)


def _fallback_response(message: str, language: str, level: str) -> str:
    return (
        f'That\'s an interesting point about "{message}". '
        f"As a {language} tutor at {level} level, "
        "I would suggest practicing this with more example sentences. "
        "(No LLM backend available — install Ollama or set POLYGLOT_LLM_MODEL_PATH)"
    )
