"""
Speech-to-Text integration for Polyglot Coach.

Uses faster-whisper for offline multilingual transcription.
"""

import os
import tempfile
from pathlib import Path

MODEL_SIZE = os.environ.get("POLYGLOT_STT_MODEL", "medium")

_whisper_model = None
_HAS_WHISPER = False

try:
    from faster_whisper import WhisperModel

    _HAS_WHISPER = True
except ImportError:
    pass


def is_stt_available() -> bool:
    return _HAS_WHISPER


def load_stt_model():
    global _whisper_model
    if not _HAS_WHISPER:
        return None
    if _whisper_model is None:
        model_dir = os.environ.get("POLYGLOT_STT_MODEL_DIR", str(Path.home() / ".polyglot-coach" / "models" / "stt"))
        _whisper_model = WhisperModel(MODEL_SIZE, download_root=model_dir, device="cpu", compute_type="int8")
    return _whisper_model


def transcribe(audio_bytes: bytes, language: str | None = None) -> dict:
    model = load_stt_model()
    if model is None:
        return {"text": "", "error": "faster-whisper not installed, run: uv pip install faster-whisper"}

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        segments, info = model.transcribe(tmp_path, language=language, beam_size=5)
        text = " ".join(seg.text for seg in segments)
        return {
            "text": text,
            "language": info.language if info else language,
            "duration": info.duration if info else 0,
        }
    finally:
        Path(tmp_path).unlink(missing_ok=True)
