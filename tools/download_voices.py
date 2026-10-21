#!/usr/bin/env python3
"""Download the Piper voices declared in models/tts/voices.yaml.

The destination filename is the manifest key (for example ``es.onnx``), which
matches the ``tts_voice`` values used by curriculum language packs and the
fallback lookup in ``apps/api/.../services/tts.py``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = PROJECT_ROOT / "models" / "tts" / "voices.yaml"
DEFAULT_VOICE_DIR = Path.home() / ".polyglot-coach" / "models" / "tts"


def _download(url: str, destination: Path) -> None:
    tmp = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, open(tmp, "wb") as out:
            shutil.copyfileobj(response, out)
        tmp.replace(destination)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def download_voices(
    manifest_path: Path,
    voice_dir: Path,
    only: set[str] | None = None,
    force: bool = False,
) -> int:
    with open(manifest_path, encoding="utf-8") as f:
        manifest = yaml.safe_load(f) or {}
    voices = manifest.get("voices") or {}
    if not voices:
        print(f"No voices declared in {manifest_path}")
        return 1

    voice_dir.mkdir(parents=True, exist_ok=True)
    failures = 0
    for key, config in voices.items():
        if only and key not in only:
            continue
        url = config.get("url")
        if not url:
            print(f"  {key}: missing url")
            failures += 1
            continue

        model_path = voice_dir / f"{key}.onnx"
        config_path = voice_dir / f"{key}.onnx.json"
        if model_path.exists() and config_path.exists() and not force:
            print(f"  {key}: already downloaded")
            continue

        print(f"  {key}: downloading {config.get('name') or key} ...")
        try:
            _download(url, model_path)
            _download(f"{url}.json", config_path)
        except (urllib.error.URLError, OSError) as exc:
            print(f"  {key}: failed — {exc}")
            failures += 1
            continue
        print(f"  {key}: saved {model_path}")

    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Download Piper TTS voices")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--voice-dir",
        type=Path,
        default=Path(os.environ.get("POLYGLOT_TTS_VOICE_DIR", DEFAULT_VOICE_DIR)),
    )
    parser.add_argument("--only", help="Comma-separated voice keys to download")
    parser.add_argument("--force", action="store_true", help="Re-download existing voices")
    args = parser.parse_args(argv)

    only = {item.strip() for item in args.only.split(",") if item.strip()} if args.only else None
    return download_voices(args.manifest, args.voice_dir, only=only, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
