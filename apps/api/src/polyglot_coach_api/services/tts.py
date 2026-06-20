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


def _voice_model_path(locale: str) -> Path | None:
    model = Path(VOICE_DIR) / f"{locale}.onnx"
    if model.exists():
        return model
    return None


def synthesize(text: str, locale: str = "en_US") -> bytes | None:
    voice = _voice_model_path(locale)
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
