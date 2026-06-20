# Architecture Overview

Polyglot Coach uses a three-layer architecture designed for offline-first conversational learning.

## Conversation Flow

```text
User Speaks → Speech To Text → Transcript Processing → Profile Loading
→ Curriculum Lookup → Learner Memory Lookup → Tutor Generation
→ Structured Response → Text To Speech → Audio Playback
```

## Three-Layer Architecture

### Voice Layer

The Voice Layer handles user audio input and spoken output.

Components:

- OpenWakeWord
- Faster Whisper
- Piper TTS

### Tutor Layer

The Tutor Layer constructs prompts, evaluates context, and generates learning-focused responses.

Components:

- Qwen3
- Curriculum Engine
- Learner Memory Engine

### MCP Layer

The MCP Layer exposes reusable educational tools and learner-state services.

Components:

- learner-memory
- curriculum
- dictionary
- grammar
- locale
- conversation
- review
- analytics

## Data Flow Between Layers

The Voice Layer captures speech and transforms it into text for the Tutor Layer.
The Tutor Layer enriches the conversation with curriculum context and learner progress from MCP services.
The final structured tutor response is returned to the Voice Layer for synthesis and playback.

## Model Recommendations

| Capability | Primary Model | Future Model |
| --- | --- | --- |
| LLM | Qwen3 8B | Qwen3 14B, Gemma 3 12B |
| STT | Faster Whisper Medium | Faster Whisper Large V3 |
| TTS | Piper TTS | Additional higher-quality locale voice packs |
