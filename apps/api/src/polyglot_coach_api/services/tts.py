"""
Text-to-Speech integration for Polyglot Coach.

Uses Piper TTS for offline voice synthesis.
"""

import importlib
import os
import subprocess
import tempfile
from pathlib import Path

_HAS_PIPER = importlib.util.find_spec("piper_tts") is not None  # type: ignore[attr-defined]

PIPER_EXECUTABLE = os.environ.get("POLYGLOT_PIPER_PATH", "piper")
VOICE_DIR = os.environ.get(
    "POLYGLOT_TTS_VOICE_DIR", str(Path.home() / ".polyglot-coach" / "models" / "tts")
)


def is_tts_available() -> bool:
    return _HAS_PIPER or _piper_binary_exists()


def _piper_binary_exists() -> bool:
    try:
        subprocess.run([PIPER_EXECUTABLE, "--help"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _voice_model_path(locale: str, language: str | None = None) -> Path | None:
    """Resolve a voice file, falling back from a locale to its base language.

    Voices are stored as ``<tts_voice>.onnx``. Language packs set
    ``tts_voice`` to values such as ``es`` or ``fr``, so ``es_MX`` should fall
    back to ``es`` when no region-specific voice is installed.
    """
    candidates: list[str] = []
    for candidate in (locale, language):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    if locale and "_" in locale:
        base = locale.split("_", 1)[0]
        if base not in candidates:
            candidates.append(base)

    for candidate in candidates:
        if candidate == "neutral":
            continue
        model = Path(VOICE_DIR) / f"{candidate}.onnx"
        if model.exists():
            return model
    return None


def synthesize(text: str, locale: str = "en_US", language: str | None = None) -> bytes | None:
    voice = _voice_model_path(locale, language)
    if not voice:
        return None

    if _piper_binary_exists():
        return _synthesize_piper_binary(text, voice)

    if _HAS_PIPER:
        return _synthesize_piper_library(text, str(voice))

    return None


def _synthesize_piper_binary(text: str, voice_path: Path) -> bytes:
    with tempfile.NamedTemporaryFile(suffix=".wav") as out:
        subprocess.run(
            [PIPER_EXECUTABLE, "--model", str(voice_path), "--output-file", out.name],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        return Path(out.name).read_bytes()


def _synthesize_piper_library(text: str, voice_path: str) -> bytes:
    import piper_tts

    pipe = piper_tts.PiperVoice.load(voice_path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
        pipe.synthesize(text, out)
        return Path(out.name).read_bytes()
