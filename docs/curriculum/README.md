# Curriculum System

Curriculum content is data so that languages, levels, and teaching material can
grow without changing core logic.

## Structure

```text
curriculum/
├── registry.yaml          # enabled languages + proficiency frameworks
├── common/                # shared resources
├── es/
│   ├── language.yaml      # metadata for the Spanish pack
│   ├── README.md
│   └── A1/
│       ├── grammar.yaml
│       ├── vocabulary.yaml
│       ├── scenarios.yaml
│       └── locale.yaml
├── fr/
├── de/
└── ja/                    # planned; no language.yaml yet
```

There is exactly one directory per ISO 639-1 language code. Name-based
directories such as `spanish/` or `french/` are not supported.

## Registry

`curriculum/registry.yaml` is the single source of truth for:

- which language codes are enabled and therefore loaded by the API
- which proficiency frameworks exist and the order of their levels
- which languages are documented but not yet shipped (`planned_languages`)

The loader only reads languages listed under `languages`. A directory with
content but no registry entry is ignored by the runtime and reported as an error
by the validator.

## Language metadata

Each `language.yaml` declares:

- `code`, `name`, `native_name`
- `level_framework` (`cefr`, `jlpt`, …)
- `levels` (a subset of the framework's levels)
- `default_level`
- `status` (`active`, `preview`, or `draft`)
- `locales`, including an optional `stt_language` and `tts_voice`
- `capabilities` (`grammar`, `vocabulary`, `scenarios`, `locale`, …)
- `script` and `direction` (`ltr` or `rtl`)
- `teaching_notes`, a short list of language-specific priorities for the tutor
- `features`, structured advanced teaching topics

Do not list a level until its directory contains real content. Spanish, French,
and German currently expose only A1.

## Advanced language features

Features are data, not core-code branches:

```yaml
features:
  - id: grammatical_case
    name: The four cases
    category: grammar
    levels: [A1]
    description: Use nominative, accusative, dative, and genitive by role.
    examples:
      - "Der Mann sieht den Hund."
      - "Ich helfe dem Mann."
```

Rules enforced by the validator:

- `id`, `name`, `category`, and `description` are required.
- `id` must match `[a-z0-9_]+` and be unique within the pack.
- `levels` must be a subset of the pack's declared levels.
- `examples`, when present, must be a list of strings.

The metadata endpoints expose features with the rest of the pack. The tutor
prompt receives the feature descriptions, script/direction, and teaching notes.
A learner can select features for a session; the API validates those ids and the
prompt marks them as the current focus. This keeps advanced language behavior
data-driven and prevents advertising features that are not declared for a level.

## Content files

- `grammar.yaml` — `rules[]` with `rule_id`, `title`, `explanation`, `examples`,
  `level`, `category`. IDs must be globally unique and start with
  `<language>_<level>_`.
- `vocabulary.yaml` — `words[]` with `word`, `translation`, optional `tags`.
  Quote YAML booleans such as `"no"` and `"yes"` so they are not parsed as
  booleans.
- `scenarios.yaml` — `scenarios[]` with `title`, `context`, `level`, `roles`,
  `vocabulary_hints`, `grammar_focus`.
- `locale.yaml` — `locale_overrides[]` and optional `pronunciation_profiles`.
  Every referenced locale must be declared in `language.yaml`. Pronunciation
  profiles are validated but not yet consumed by the locale MCP, which still
  has hardcoded profiles.

## Proficiency levels

- Spanish, French, and German use CEFR.
- Japanese will use JLPT (`N5`–`N1`).

Framework definitions live in the registry. The validator rejects a level that
is not part of the pack's declared framework.

## Adding a language

1. Create `curriculum/<code>/language.yaml`.
2. Add at least one complete level directory.
3. Enable the code in `curriculum/registry.yaml`.
4. Add voice assets to `models/tts/voices.yaml` if TTS is supported.
5. Declare `script`, `direction`, `teaching_notes`, and `features`.
6. Run `uv run python tools/validate_curriculum.py`.
7. Run `uv run pytest`.

Use `tools/generate-curriculum.py scaffold` to create the directory structure,
then replace the template content.

The API metadata endpoints and web selectors read the registry, so a new enabled
pack becomes selectable without frontend code changes. Levels and locales are
filtered from the pack, and invalid selections receive HTTP 422.

## Validation

```bash
uv run python tools/validate_curriculum.py
uv run python tools/validate_curriculum.py --strict
uv run python tools/validate_curriculum.py --json
```

The validator checks registry consistency, pack metadata, framework/level
membership, content schemas, ID uniqueness, locale references, and placeholder
content. CI and local tests run it against the real curriculum.

## MCP Integration

The Curriculum MCP reads the seeded SQLite tables to select lessons, topics,
objectives, and scenario prompts that match the learner's language, locale, and
proficiency.
