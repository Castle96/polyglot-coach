"""Read-only metadata endpoints for languages, levels, locales, and features."""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException

from polyglot_coach_shared.languages import (
    features_for,
    get_language,
    list_public_languages,
    load_registry,
    public_language,
    resolve_selection,
)

router = APIRouter()

PROJECT_ROOT = Path(
    os.environ.get("POLYGLOT_PROJECT_ROOT", Path(__file__).resolve().parents[5])
)
VOICE_MANIFEST = PROJECT_ROOT / "models" / "tts" / "voices.yaml"
VOICE_DIR = os.environ.get(
    "POLYGLOT_TTS_VOICE_DIR", str(Path.home() / ".polyglot-coach" / "models" / "tts")
)


@router.get("/languages")
def api_list_languages():
    return {"languages": list_public_languages()}


@router.get("/languages/{code}")
def api_get_language(code: str):
    language = public_language(code)
    if language is None:
        raise HTTPException(404, f"Language '{code}' is not enabled")
    return language


@router.get("/languages/{code}/features")
def api_get_language_features(code: str, level: str | None = None):
    if get_language(code) is None:
        raise HTTPException(404, f"Language '{code}' is not enabled")
    if level is not None:
        try:
            _, level, _ = resolve_selection(code, level=level)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"language": code, "level": level, "features": features_for(code, level)}


@router.get("/frameworks")
def api_list_frameworks():
    registry = load_registry()
    return {
        "frameworks": [
            {"id": framework_id, **data}
            for framework_id, data in registry.get("level_frameworks", {}).items()
        ]
    }


@router.get("/voices")
def api_list_voices():
    """Report declared TTS voices and whether their files are installed."""
    if not VOICE_MANIFEST.exists():
        return {"voices": [], "voice_dir": VOICE_DIR}
    with open(VOICE_MANIFEST, encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}
    voice_dir = Path(VOICE_DIR)
    voices = []
    for key, data in (manifest.get("voices") or {}).items():
        entry = data if isinstance(data, dict) else {}
        voices.append(
            {
                "key": key,
                "name": entry.get("name") or key,
                "installed": (voice_dir / f"{key}.onnx").exists(),
            }
        )
    return {"voices": voices, "voice_dir": str(voice_dir)}
