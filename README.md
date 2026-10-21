# Polyglot Coach

> Local-first AI language tutoring, powered by open models.

![Status](https://img.shields.io/badge/status-phase%201-yellow)
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

## Project Status

This repository is an early implementation. The core API, SQLite storage, MCP
services, web chat client, and three language packs are functional.

Working today:

- FastAPI tutor endpoints backed by Ollama or a local GGUF model
- SQLite learner memory, mistakes, review scheduling, and progress records
- MCP services for learner memory, curriculum, dictionary, grammar, locale,
  conversation, review, and analytics
- A single-page web chat client served by the API
- Spanish, French, and German A1 language packs
- Registry-driven curriculum loading and validation
- Registry-backed language, level, locale, framework, and feature metadata endpoints
- Dynamic web selectors and per-language advanced feature focus
- Server-side validation of language, level, locale, and feature combinations

Not implemented yet:

- Speech-to-text and text-to-speech API endpoints (service modules exist but
  are not wired to the API)
- Wake word detection
- Japanese curriculum (planned; see `curriculum/ja/README.md`)
- A2–C1 content, despite earlier versions of this README claiming full coverage
- Feature-specific exercise banks; advanced features guide prompts and examples
  but do not yet have standalone drill sets
- Interface localization (the UI is English-only)
- Desktop application
- Authentication, multi-user isolation, and production hardening

## Supported Languages

Coverage below reflects the content actually present in the repository, not the
aspirational level range.

| Language | Code | Locales | Levels with content | Status |
| --- | --- | --- | --- | --- |
| Spanish | `es` | `neutral`, `es_ES`, `es_MX` | A1 | Active — 40 words, 10 rules, 6 scenarios |
| French | `fr` | `neutral`, `fr_FR`, `fr_CA` | A1 | Preview — 28 words, 3 rules, 3 scenarios; `fr_CA` overrides pending |
| German | `de` | `neutral`, `de_DE` | A1 | Preview — 27 words, 3 rules, 3 scenarios |
| Japanese | `ja` | `ja_JP` (planned) | None | Not available — N5–N1 planned |

The registry is the source of truth: `curriculum/registry.yaml`. Run the
validator for the current numbers:

```bash
uv run python tools/validate_curriculum.py
```

Each active pack also declares advanced teaching features. These are metadata,
not hardcoded per-language branches, and are injected into tutor prompts:

| Language | Advanced features |
| --- | --- |
| Spanish | ser vs. estar, gender/number agreement, formal address, regional variation, pronunciation |
| French | gender/agreement, tu vs. vous, elision/liaison, accents, regional variation |
| German | four cases, gender/articles, verb-second order, separable verbs, du vs. Sie |

Learners can select one or more features in the web sidebar. The tutor then
prioritizes them while keeping the conversation natural. The same selection can
be sent through the API with the `features` field.

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

The voice stages are not wired into the API yet. The current working path is
text input → tutor generation → text response.

## Tech Stack

| Area | Current Implementation | Notes |
| --- | --- | --- |
| LLM | Qwen2.5 7B | Default Ollama model; local GGUF via llama-cpp-python is also supported |
| Speech To Text | Faster Whisper Medium | Service module only; no API endpoint yet |
| Text To Speech | Piper TTS | Service module and voice manifest only; no API endpoint yet |
| Wake Word | Not implemented | OpenWakeWord is a future integration |
| Storage | SQLite | Local learner memory and analytics |
| API | FastAPI | Serves the REST API and the bundled web client |
| Web | Static HTML/CSS/JS | Served directly by the API; not yet a packaged frontend |

## Learning Modes

- Conversation
- Lesson
- Grammar Focus
- Vocabulary Focus
- Roleplay
- Assessment
- Immersion

Mode aliases are normalised in `services/prompts.py` (`tutor` → conversation,
`scenario` → roleplay, and so on). The web selector exposes the canonical modes.

## Repository Structure

```text
polyglot-coach/
├── apps/
│   ├── api/                 # FastAPI service, loader, LLM/STT/TTS modules
│   ├── desktop/             # Placeholder
│   └── web/                 # Single-page chat client
├── curriculum/
│   ├── registry.yaml        # Enabled languages and level frameworks
│   ├── common/
│   ├── de/                  # Canonical German pack (language.yaml + A1/)
│   ├── es/                  # Canonical Spanish pack (language.yaml + A1/)
│   ├── fr/                  # Canonical French pack (language.yaml + A1/)
│   └── ja/                  # Planned Japanese pack (README only)
├── datasets/                # Planned shared datasets (README placeholders)
├── docs/
│   ├── api/
│   ├── architecture/
│   ├── curriculum/
│   └── mcp/
├── mcp/                     # MCP services, one package per service
├── models/
│   ├── llm/
│   ├── stt/
│   └── tts/                 # Piper voice manifest: voices.yaml
├── profiles/                # Planned learner/language profiles
├── storage/
│   ├── migrations/
│   └── sqlite/
├── tests/
└── tools/
    ├── download_voices.py
    ├── generate-curriculum.py
    └── validate_curriculum.py
```

There is one canonical directory per ISO 639-1 language code. Earlier
name-based directories (`curriculum/spanish`, `curriculum/french`,
`curriculum/german`, `curriculum/japanese`) have been removed.

## Getting Started

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- [Ollama](https://ollama.ai) or a local GGUF model
- Node 20+ and [pnpm](https://pnpm.io/) only when working on future packaged
  frontend code; the bundled web client is static and needs no Node build

### Clone and install

```bash
git clone https://github.com/Castle96/polyglot-coach.git
cd polyglot-coach
uv sync
```

### Download models

```bash
./run.sh --download-models
```

This pulls the default Ollama model and downloads the Piper voices declared in
`models/tts/voices.yaml`. Faster Whisper downloads on first use.

### Run

```bash
./run.sh
```

The API and web client are available at <http://localhost:8000>. API docs are at
<http://localhost:8000/docs>.

### Validate curriculum

```bash
uv run python tools/validate_curriculum.py
uv run python tools/validate_curriculum.py --strict
```

### Tests

```bash
uv run pytest
```

## Language Packs

A language pack is metadata plus level content:

```text
curriculum/es/
├── language.yaml
├── README.md
└── A1/
    ├── grammar.yaml
    ├── vocabulary.yaml
    ├── scenarios.yaml
    └── locale.yaml
```

`language.yaml` declares the language identity, proficiency framework, enabled
levels, locales, script, and advanced teaching features:

```yaml
code: es
name: Spanish
native_name: Español
level_framework: cefr
levels: [A1]
default_level: A1
status: active

locales:
  neutral: {name: Neutral Spanish, stt_language: es, tts_voice: es}
  es_ES:   {name: Spain, stt_language: es, tts_voice: es}
  es_MX:   {name: Mexico, stt_language: es, tts_voice: es}

capabilities: [grammar, vocabulary, scenarios, locale]
script: Latin
direction: ltr

teaching_notes:
  - "Ser describes identity, origin, and inherent characteristics; estar describes states."

features:
  - id: ser_estar
    name: Ser vs. estar
    category: grammar
    levels: [A1]
    description: Choose the correct copula for identity, origin, state, or location.
    examples:
      - "Soy estudiante."
      - "Estoy cansado."
```

Feature `id` values are stable, lowercase identifiers. `levels` limits a feature
to the levels where it should be taught. The API exposes features through the
metadata endpoints, and the tutor prompt receives the descriptions plus any
learner-selected focus.

`curriculum/registry.yaml` enables packs and defines proficiency frameworks:

```yaml
version: 1
default_language: es
level_frameworks:
  cefr:
    levels: [A1, A2, B1, B2, C1, C2]
  jlpt:
    levels: [N5, N4, N3, N2, N1]
languages: [es, fr, de]
```

### Adding a language

1. Create `curriculum/<code>/language.yaml` using the schema above.
2. Add at least one complete level directory (for example `A1/` or `N5/`).
3. Add the code to `languages` in `curriculum/registry.yaml` and remove it from
   `planned_languages`.
4. Add a voice entry to `models/tts/voices.yaml` if TTS is supported.
5. Run `uv run python tools/validate_curriculum.py`.
6. Run `uv run pytest`.

The API loader only reads languages and levels declared in the registry, so a
half-finished language pack cannot leak into tutoring sessions.

### Metadata and advanced feature selection

The web client loads its selectors from the registry instead of hardcoding
languages or levels:

- `GET /api/v1/meta/languages` — enabled languages, levels, locales, script,
  status, capabilities, and advanced features
- `GET /api/v1/meta/languages/{code}` — one language pack
- `GET /api/v1/meta/languages/{code}/features?level=A1` — features for a level
- `GET /api/v1/meta/frameworks` — CEFR, JLPT, and any other registered framework
- `GET /api/v1/meta/voices` — declared Piper voices and whether files are installed
- `GET /api/v1/tutor/options?language=es` — resolved level and feature options

Tutor requests accept optional `level`, `locale`, and `features` fields. The API
validates all three against the pack before invoking the model and returns HTTP
422 for unsupported combinations:

```json
{
  "profile_id": 1,
  "message": "Quiero practicar ser y estar.",
  "language": "es",
  "level": "A1",
  "locale": "es_MX",
  "mode": "grammar",
  "features": ["ser_estar", "formality"]
}
```

Omitting `level` or `locale` selects the pack default. Feature focus is injected
as structured prompt context; it does not change the curriculum content itself.

### Level frameworks

Levels are not assumed to be CEFR. Each pack names a framework from the
registry. Japanese will use JLPT (`N5`–`N1`), and the validator rejects levels
that do not belong to the declared framework.

### Locales and voices

Locale overrides live in each level's `locale.yaml`. The `tts_voice` value in
`language.yaml` maps a locale to a Piper voice key in
`models/tts/voices.yaml`. `tools/download_voices.py` stores voices as
`<key>.onnx`, matching the runtime lookup in `services/tts.py`.

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

## Docker and Kubernetes

```bash
docker compose up --build
```

The Compose and Kubernetes manifests mount the curriculum and storage
directories and set `POLYGLOT_CURRICULUM_PATH` and `POLYGLOT_DB_PATH`
explicitly. The image also includes the curriculum as a fallback for standalone
runs.

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
coding standards, and pull request guidance.

When adding a language, include the pack, a registry entry, validation, and
tests. Do not advertise a language or level in the README before its content
exists.

## License

No license has been selected yet. Until a license is added, the repository is
not licensed for redistribution.
