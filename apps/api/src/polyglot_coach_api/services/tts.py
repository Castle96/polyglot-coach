"""
Text-to-Speech integration for Polyglot Coach.

Uses Piper TTS for offline voice synthesis.
"""

import os
import shutil
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

try:
    from piper.voice import PiperVoice

    _HAS_PIPER = True
except ImportError:
    _HAS_PIPER = False

PIPER_EXECUTABLE = os.environ.get("POLYGLOT_PIPER_PATH", "piper")
VOICE_DIR = os.environ.get(
    "POLYGLOT_TTS_VOICE_DIR", str(Path.home() / ".polyglot-coach" / "models" / "tts")
)


def is_tts_available() -> bool:
    return _HAS_PIPER or _piper_binary_exists()


@lru_cache(maxsize=1)
def _piper_binary_exists() -> bool:
    executable = shutil.which(PIPER_EXECUTABLE)
    if executable is None:
        return False
    try:
        subprocess.run([executable, "--help"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
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

    if _HAS_PIPER:
        return _synthesize_piper_library(text, str(voice))

    if _piper_binary_exists():
        return _synthesize_piper_binary(text, voice)

    return None


def _synthesize_piper_binary(text: str, voice_path: Path) -> bytes | None:
    with tempfile.NamedTemporaryFile(suffix=".wav") as out:
        result = subprocess.run(
            [PIPER_EXECUTABLE, "--model", str(voice_path), "--output_file", out.name],
            input=text.encode("utf-8"),
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        return Path(out.name).read_bytes()


def _synthesize_piper_library(text: str, voice_path: str) -> bytes | None:
    pipe = PiperVoice.load(voice_path)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out:
        output_path = Path(out.name)

    try:
        with wave.open(str(output_path), "wb") as wav_file:
            pipe.synthesize(text, wav_file)
        return output_path.read_bytes()
    finally:
        output_path.unlink(missing_ok=True)
