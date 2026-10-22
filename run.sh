#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

MODEL_DIR="${POLYGLOT_MODEL_DIR:-$HOME/.polyglot-coach/models}"

# Default to persistent DB in the project dir
export POLYGLOT_DB_PATH="${POLYGLOT_DB_PATH:-$SCRIPT_DIR/data/polyglot.db}"
export POLYGLOT_CURRICULUM_PATH="${POLYGLOT_CURRICULUM_PATH:-$SCRIPT_DIR/curriculum}"

# ------------------------------------------------------------------
# LLM — OpenAI-compatible (bring your own key), Ollama, or local GGUF
# ------------------------------------------------------------------
LLM_PROVIDER="${POLYGLOT_LLM_PROVIDER:-auto}"
case "$LLM_PROVIDER" in
    auto|openai|ollama|llama-cpp) ;;
    *)
        echo "WARNING: unknown POLYGLOT_LLM_PROVIDER='$LLM_PROVIDER'; using auto."
        LLM_PROVIDER=auto
        ;;
esac
export POLYGLOT_LLM_PROVIDER="$LLM_PROVIDER"

export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
export POLYGLOT_LLM_MODEL_PATH="${POLYGLOT_LLM_MODEL_PATH:-$MODEL_DIR/llm/qwen2.5-7b-q4.gguf}"

OPENAI_BASE_URL="${POLYGLOT_OPENAI_BASE_URL:-https://api.openai.com/v1}"
OPENAI_MODEL="${POLYGLOT_OPENAI_MODEL:-gpt-4o-mini}"

# Match the API's precedence: auto uses OpenAI only with the dedicated
# POLYGLOT_OPENAI_API_KEY variable; a bare OPENAI_API_KEY requires an explicit
# POLYGLOT_LLM_PROVIDER=openai.
USE_OPENAI=0
if [ "$LLM_PROVIDER" = "openai" ] || { [ "$LLM_PROVIDER" = "auto" ] && [ -n "${POLYGLOT_OPENAI_API_KEY:-}" ]; }; then
    USE_OPENAI=1
fi

USE_OLLAMA=0
if [ "$USE_OPENAI" -eq 0 ] && { [ "$LLM_PROVIDER" = "auto" ] || [ "$LLM_PROVIDER" = "ollama" ]; }; then
    USE_OLLAMA=1
fi

if [ "$USE_OPENAI" -eq 1 ]; then
    if [ -n "${POLYGLOT_OPENAI_API_KEY:-}" ]; then
        echo "LLM: OpenAI-compatible ($OPENAI_MODEL at $OPENAI_BASE_URL)"
    elif [ -n "${OPENAI_API_KEY:-}" ]; then
        echo "LLM: OpenAI-compatible ($OPENAI_MODEL at $OPENAI_BASE_URL, using OPENAI_API_KEY)"
    else
        echo "WARNING: OpenAI-compatible provider selected but no API key is set."
        echo "         Set POLYGLOT_OPENAI_API_KEY (or OPENAI_API_KEY) and restart."
    fi
elif [ "$LLM_PROVIDER" = "llama-cpp" ]; then
    echo "LLM: llama-cpp GGUF ($POLYGLOT_LLM_MODEL_PATH)"
elif command -v ollama &>/dev/null; then
    echo "Ollama: found ($(ollama --version 2>/dev/null || echo 'unknown'))"
    echo "LLM: $OLLAMA_MODEL (via Ollama)"
else
    echo "Ollama: not installed — see https://ollama.ai"
    echo "LLM: no local backend available; set POLYGLOT_OPENAI_API_KEY or install Ollama."
fi

# ------------------------------------------------------------------
# STT  (faster-whisper auto-downloads to this dir on first use)
# ------------------------------------------------------------------
export POLYGLOT_STT_MODEL="${POLYGLOT_STT_MODEL:-medium}"
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

    # 1. LLM
    if [ "$USE_OPENAI" -eq 1 ]; then
        echo ">>> LLM: using OpenAI-compatible provider; no model download needed."
        echo "    Model: $OPENAI_MODEL"
        echo "    Base:  $OPENAI_BASE_URL"
        echo ""
    elif [ "$USE_OLLAMA" -eq 1 ]; then
        if command -v ollama &>/dev/null; then
            echo ">>> Pulling $OLLAMA_MODEL via Ollama ..."
            ollama pull "$OLLAMA_MODEL"
            echo ""
        else
            echo ">>> Install Ollama first: https://ollama.ai"
            echo "    Then run: ollama pull $OLLAMA_MODEL"
            echo ""
        fi
    else
        echo ">>> LLM: llama-cpp selected; expected GGUF at $POLYGLOT_LLM_MODEL_PATH"
        if [ ! -f "$POLYGLOT_LLM_MODEL_PATH" ]; then
            echo "    WARNING: GGUF file not found."
        fi
        echo ""
    fi

    # 2. STT — faster-whisper downloads on first use, nothing to do here
    echo ">>> STT: faster-whisper will auto-download on first API call"
    echo "    Model: $POLYGLOT_STT_MODEL"
    echo "    Target: $POLYGLOT_STT_MODEL_DIR"
    echo ""

    # 3. TTS — Piper voices (manifest: models/tts/voices.yaml)
    echo ">>> Downloading Piper TTS voices ..."
    mkdir -p "$POLYGLOT_TTS_VOICE_DIR"
    uv run python tools/download_voices.py --voice-dir "$POLYGLOT_TTS_VOICE_DIR"

    echo ""
    echo "============================================"
    echo " All models ready!"
    if [ "$USE_OPENAI" -eq 1 ]; then
        echo "    LLM:  $OPENAI_MODEL (OpenAI-compatible)"
    elif [ "$LLM_PROVIDER" = "llama-cpp" ]; then
        echo "    LLM:  $POLYGLOT_LLM_MODEL_PATH"
    else
        echo "    LLM:  ollama run $OLLAMA_MODEL"
    fi
    echo "    STT:  $POLYGLOT_STT_MODEL ($POLYGLOT_STT_MODEL_DIR)"
    echo "    TTS:  $POLYGLOT_TTS_VOICE_DIR"
    echo "============================================"
    exit 0
fi

echo ""
echo "Starting Polyglot Coach API on http://localhost:8000"
echo "  Curriculum: $POLYGLOT_CURRICULUM_PATH"
echo "  Database:   $POLYGLOT_DB_PATH"
if [ "$USE_OPENAI" -eq 1 ]; then
    echo "  LLM:        $OPENAI_MODEL (OpenAI-compatible)"
elif [ "$LLM_PROVIDER" = "llama-cpp" ]; then
    echo "  LLM:        $POLYGLOT_LLM_MODEL_PATH (llama-cpp)"
else
    echo "  LLM:        $OLLAMA_MODEL (via Ollama)"
fi
echo "  STT:        $POLYGLOT_STT_MODEL"
echo "  TTS:        $POLYGLOT_TTS_VOICE_DIR"
echo ""

# Provisioning is explicit: backend detection never pulls models.
if [ "$USE_OLLAMA" -eq 1 ] && command -v ollama &>/dev/null; then
    if ! ollama list 2>/dev/null | awk 'NR > 1 { print $1 }' | grep -qx "$OLLAMA_MODEL"; then
        echo "Ollama model $OLLAMA_MODEL is not installed; pulling it now..."
        ollama pull "$OLLAMA_MODEL" || \
            echo "WARNING: could not pull $OLLAMA_MODEL; the API will run without an LLM."
    fi
fi

uv run uvicorn polyglot_coach_api.main:app --host 0.0.0.0 --port 8000 --reload
