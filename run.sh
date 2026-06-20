#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODEL_DIR="${POLYGLOT_MODEL_DIR:-$HOME/.polyglot-coach/models}"

# Default to persistent DB in the project dir
export POLYGLOT_DB_PATH="${POLYGLOT_DB_PATH:-$SCRIPT_DIR/data/polyglot.db}"
export POLYGLOT_CURRICULUM_PATH="${POLYGLOT_CURRICULUM_PATH:-$SCRIPT_DIR/curriculum}"

# ------------------------------------------------------------------
# LLM  — Ollama (recommended) or local GGUF via llama-cpp-python
# ------------------------------------------------------------------
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
export POLYGLOT_LLM_MODEL_PATH="${POLYGLOT_LLM_MODEL_PATH:-$MODEL_DIR/llm/qwen2.5-7b-q4.gguf}"

if command -v ollama &>/dev/null; then
    echo "Ollama: found ($(ollama --version 2>/dev/null || echo 'unknown'))"
else
    echo "Ollama: not installed — see https://ollama.ai"
fi

# ------------------------------------------------------------------
# STT  (faster-whisper auto-downloads to this dir on first use)
# ------------------------------------------------------------------
export POLYGLOT_STT_MODEL="${POLYGLOT_STT_MODEL:-large-v3}"
export POLYGLOT_STT_MODEL_DIR="${POLYGLOT_STT_MODEL_DIR:-$MODEL_DIR/stt}"
mkdir -p "$POLYGLOT_STT_MODEL_DIR"

# ------------------------------------------------------------------
# TTS  (Piper voice .onnx files — downloaded from open repos)
# ------------------------------------------------------------------
export POLYGLOT_TTS_VOICE_DIR="${POLYGLOT_TTS_VOICE_DIR:-$MODEL_DIR/tts}"
mkdir -p "$POLYGLOT_TTS_VOICE_DIR"

# ------------------------------------------------------------------
# Download all models
# ------------------------------------------------------------------
if [ "${1:-}" = "--download-models" ]; then
    echo ""
    echo "============================================"
    echo " Downloading models for Polyglot Coach"
    echo "============================================"
    echo ""

    # 1. LLM — via Ollama
    if command -v ollama &>/dev/null; then
        echo ">>> Pulling $OLLAMA_MODEL via Ollama ..."
        ollama pull "$OLLAMA_MODEL"
        echo ""
    else
        echo ">>> Install Ollama first: https://ollama.ai"
        echo "    Then run: ollama pull $OLLAMA_MODEL"
        echo ""
    fi

    # 2. STT — faster-whisper downloads on first use, nothing to do here
    echo ">>> STT: faster-whisper will auto-download on first API call"
    echo "    Model: $POLYGLOT_STT_MODEL"
    echo "    Target: $POLYGLOT_STT_MODEL_DIR"
    echo ""

    # 3. TTS — Piper voices
    echo ">>> Downloading Piper TTS voices ..."
    mkdir -p "$POLYGLOT_TTS_VOICE_DIR"
    download_voice() {
        local locale="$1" url="$2"
        local out="$POLYGLOT_TTS_VOICE_DIR/${locale}.onnx"
        local json_out="$POLYGLOT_TTS_VOICE_DIR/${locale}.onnx.json"
        if [ ! -f "$out" ]; then
            echo "    Downloading $locale voice ..."
            wget -q --show-progress -O "$out" "$url"
            wget -q --show-progress -O "$json_out" "${url}.json"
        else
            echo "    $locale voice: already downloaded"
        fi
    }

    download_voice "es" "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/carlfm/medium/es_ES-carlfm-medium.onnx"
    download_voice "fr" "https://huggingface.co/rhasspy/piper-voices/resolve/main/fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx"
    download_voice "de" "https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx"

    echo ""
    echo "============================================"
    echo " All models ready!"
    echo "    LLM:  ollama run $OLLAMA_MODEL"
    echo "    STT:  $POLYGLOT_STT_MODEL ($POLYGLOT_STT_MODEL_DIR)"
    echo "    TTS:  $POLYGLOT_TTS_VOICE_DIR"
    echo "============================================"
    exit 0
fi

echo ""
echo "Starting Polyglot Coach API on http://localhost:8000"
echo "  Curriculum: $POLYGLOT_CURRICULUM_PATH"
echo "  Database:   $POLYGLOT_DB_PATH"
echo "  LLM:        $OLLAMA_MODEL (via Ollama)"
echo "  STT:        $POLYGLOT_STT_MODEL"
echo "  TTS:        $POLYGLOT_TTS_VOICE_DIR"
echo ""

uv run uvicorn polyglot_coach_api.main:app --host 0.0.0.0 --port 8000 --reload
