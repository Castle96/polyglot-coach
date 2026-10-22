"""Offline speech-to-text and text-to-speech endpoints."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from polyglot_coach_api.services.stt import (
    MODEL_SIZE as STT_MODEL_SIZE,
    is_stt_available,
    transcribe,
)
from polyglot_coach_api.services.tts import VOICE_DIR, is_tts_available, synthesize
from polyglot_coach_api.validation import resolve_language_request

router = APIRouter()

AUDIO_SUFFIXES = {".wav", ".webm", ".ogg", ".mp3", ".m4a", ".flac"}
MAX_AUDIO_BYTES = 15 * 1024 * 1024


class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    language: str
    level: str | None = None
    locale: str | None = None


def _locale_setting(pack: dict, locale: str, key: str, fallback: str) -> str:
    locales = pack.get("locales") or {}
    entry = locales.get(locale) or {}
    return entry.get(key) or fallback


@router.get("/status")
def api_speech_status():
    return {
        "stt_available": is_stt_available(),
        "tts_available": is_tts_available(),
        "stt_model": STT_MODEL_SIZE,
        "tts_voice_dir": str(Path(VOICE_DIR)),
    }


@router.post("/transcribe")
async def api_transcribe(
    audio: UploadFile = File(..., description="Recorded audio (wav, webm, ogg, mp3, m4a, or flac)"),
    language: str = Form(..., description="Target language code (ISO 639-1)"),
    level: str | None = Form(None),
    locale: str | None = Form(None),
):
    """Transcribe uploaded audio using the local Faster Whisper model."""
    pack, level, locale = resolve_language_request(language, level=level, locale=locale)
    if not is_stt_available():
        raise HTTPException(
            503,
            "Speech-to-text is not installed. Run `uv sync --extra speech` and restart the API.",
        )

    data = await audio.read(MAX_AUDIO_BYTES + 1)
    if not data:
        raise HTTPException(422, "Audio upload is empty.")
    if len(data) > MAX_AUDIO_BYTES:
        raise HTTPException(
            413,
            f"Audio upload exceeds the {MAX_AUDIO_BYTES // (1024 * 1024)} MB limit.",
        )

    suffix = Path(audio.filename or "").suffix.lower()
    if suffix not in AUDIO_SUFFIXES:
        suffix = ".wav"

    try:
        result = await run_in_threadpool(
            transcribe,
            data,
            language=_locale_setting(pack, locale, "stt_language", language),
            suffix=suffix,
        )
    except Exception as exc:
        raise HTTPException(500, f"Transcription failed: {exc}") from exc

    if result.get("error"):
        raise HTTPException(503, result["error"])

    return {
        "text": result.get("text", "").strip(),
        "detected_language": result.get("language"),
        "duration": result.get("duration", 0),
        "language": language,
        "level": level,
        "locale": locale,
    }


@router.post("/synthesize")
async def api_synthesize(body: SynthesizeRequest):
    """Synthesize tutor text with a locally installed Piper voice."""
    pack, level, locale = resolve_language_request(
        body.language,
        level=body.level,
        locale=body.locale,
    )
    if not is_tts_available():
        raise HTTPException(
            503,
            "Text-to-speech is not installed. Run `uv sync --extra speech` and restart the API.",
        )

    try:
        audio = await run_in_threadpool(
            synthesize,
            body.text,
            locale=_locale_setting(pack, locale, "tts_voice", locale),
            language=body.language,
        )
    except Exception as exc:
        raise HTTPException(500, f"Speech synthesis failed: {exc}") from exc

    if not audio:
        raise HTTPException(
            503,
            f"No Piper voice is installed for {body.language}/{locale}. "
            f"Run `uv run python tools/download_voices.py`. Voice directory: {VOICE_DIR}",
        )

    return Response(
        content=audio,
        media_type="audio/wav",
        headers={
            "Content-Disposition": 'inline; filename="speech.wav"',
            "Cache-Control": "no-store",
            "X-Polyglot-Language": body.language,
            "X-Polyglot-Level": level,
            "X-Polyglot-Locale": locale,
        },
    )
