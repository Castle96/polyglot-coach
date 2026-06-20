# Polyglot Coach

> Local-first AI language tutoring, powered by open models.

![Build](https://img.shields.io/badge/build-placeholder-lightgrey)
![License](https://img.shields.io/badge/license-placeholder-lightgrey)
![Python](https://img.shields.io/badge/python-3.12%2B-blue)
![Node](https://img.shields.io/badge/node-20%2B-green)

## Vision

Polyglot Coach is a local-first AI language tutoring platform designed to provide
immersive conversational language learning without relying on cloud services.

Unlike traditional translation applications, Polyglot Coach acts as a bilingual tutor that:

- Teaches through conversation
- Adapts to learner proficiency
- Explains grammar in context
- Reinforces vocabulary through repetition
- Tracks learner progress
- Supports multiple dialects and locales
- Operates fully offline

The platform is designed to be extensible so that new languages, dialects, curricula,
and teaching methods can be added through data and MCP services without rewriting core logic.

## Supported Languages

| Language | Locales | Levels |
| --- | --- | --- |
| Spanish | es_ES, es_MX, Neutral | A1-C1 |
| French | fr_FR, fr_CA | A1-C1 |
| German | de_DE | A1-C1 |
| Japanese | ja_JP | N5-N1 |

## Architecture Overview

```text
User Speaks → Speech To Text → Transcript Processing → Profile Loading
→ Curriculum Lookup → Learner Memory Lookup → Tutor Generation
→ Structured Response → Text To Speech → Audio Playback
```

Polyglot Coach is organised into three collaborating layers:

- **Voice Layer** for wake word detection, speech recognition, and audio playback
- **Tutor Layer** for prompt construction, lesson context, and response generation
- **MCP Layer** for educational tooling, learner state, and curriculum services

## Tech Stack

| Area | Primary Technology | Notes |
| --- | --- | --- |
| LLM | Qwen3 8B | Local multilingual tutoring and instruction |
| Speech To Text | Faster Whisper Medium | Offline multilingual transcription |
| Text To Speech | Piper TTS | Locale-aware voice synthesis |
| Wake Word | OpenWakeWord | Local wake word detection |
| Storage | SQLite | Local learner memory and analytics |

## Learning Modes

- Tutor
- Immersion
- Conversation
- Scenario
- Story

## Repository Structure

```text
polyglot-coach/
├── apps/
│   ├── api/
│   ├── desktop/
│   └── web/
├── curriculum/
│   ├── common/
│   ├── french/
│   ├── german/
│   ├── japanese/
│   └── spanish/
├── datasets/
│   ├── conversations/
│   ├── examples/
│   ├── grammar/
│   ├── locales/
│   └── vocabulary/
├── docs/
│   ├── api/
│   ├── architecture/
│   ├── curriculum/
│   └── mcp/
├── mcp/
│   ├── analytics/
│   ├── conversation/
│   ├── curriculum/
│   ├── dictionary/
│   ├── grammar/
│   ├── learner-memory/
│   ├── locale/
│   └── review/
├── models/
│   ├── llm/
│   ├── stt/
│   └── tts/
├── profiles/
│   ├── french/
│   ├── german/
│   ├── japanese/
│   └── spanish/
├── storage/
│   ├── migrations/
│   └── sqlite/
└── tests/
```

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- Node 20+
- [pnpm](https://pnpm.io/)

### Clone the repository

```bash
git clone https://github.com/Castle96/polyglot-coach.git
cd polyglot-coach
```

### Install dependencies

```bash
uv sync
pnpm install
```

## MCP Services

| Service | Purpose | Example Tools |
| --- | --- | --- |
| learner-memory | Store and retrieve learner progress and history | `get_profile`, `update_profile`, `record_mistake`, `get_progress` |
| curriculum | Select lessons, topics, and guided scenarios | `get_lesson`, `get_topic`, `get_scenario` |
| dictionary | Provide definitions, examples, and conjugations | `lookup_word`, `get_examples`, `get_conjugation` |
| grammar | Explain rules and evaluate grammar exercises | `lookup_rule`, `explain_rule`, `generate_exercise`, `grade_exercise` |
| locale | Manage dialects, vocabulary overrides, and pronunciation | `get_locale`, `vocabulary_overrides`, `pronunciation_profile` |
| conversation | Generate roleplay experiences and dialogue follow-ups | `generate_scenario`, `evaluate_response`, `suggest_followup` |
| review | Schedule spaced repetition and review sessions | `get_due_words`, `schedule_review`, `record_review` |
| analytics | Summarise learner activity and progress trends | Placeholder analytics tools for retention, progress, and engagement summaries |

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
coding standards, and pull request guidance.

## License

License information will be added in a future update.
