# API Layer

The FastAPI app in `apps/api` is the local bridge between user-facing clients,
the MCP services, SQLite storage, and on-device model runtimes.

## Responsibilities

- Accept requests from the web client (and future desktop client)
- Coordinate curriculum, learner-memory, review, and locale lookups
- Manage access to local LLM, STT, and TTS runtimes
- Return structured responses suitable for tutoring workflows
- Serve the static web client

## Current endpoints

- `/api/v1/meta` — languages, levels, locales, frameworks, features, voices
- `/api/v1/learner` — profiles, mistakes, progress
- `/api/v1/curriculum` — lessons, topics, scenarios
- `/api/v1/dictionary`, `/api/v1/grammar`, `/api/v1/locale`
- `/api/v1/conversation`, `/api/v1/review`, `/api/v1/analytics`
- `/api/v1/speech` — local transcription and synthesis
- `/api/v1/tutor` — chat, quick-chat, status, and options
- `/health` — database, LLM, STT/TTS, and curriculum status
- `/readyz` — readiness probe; 503 unless the database and registry are usable

Health and readiness checks never download or provision models. The configured
Ollama model is pulled by `./run.sh` (or explicitly with `ollama pull`) so probes
cannot trigger a multi-gigabyte download.

## Language metadata

The registry in `curriculum/registry.yaml` is the source of truth. The web client
does not hardcode language or level options; it calls:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/meta/languages` | Enabled languages with levels, locales, script, status, capabilities, and features |
| `GET /api/v1/meta/languages/{code}` | One client-facing language pack |
| `GET /api/v1/meta/languages/{code}/features?level=A1` | Features valid at a level |
| `GET /api/v1/meta/frameworks` | Registered proficiency frameworks (CEFR, JLPT, …) |
| `GET /api/v1/meta/voices` | Declared Piper voices and local install status |
| `GET /api/v1/tutor/options?language=es` | Resolved level and feature options |

Adding a registry-enabled pack makes it selectable without frontend changes.

## Selection validation

Tutor, curriculum, conversation, grammar, dictionary, locale, and learner-profile
requests validate selections against the target pack. Invalid languages, levels,
locales, or features return HTTP 422 with the valid options in the detail
message. Omitting `level` or `locale` on tutor requests uses the pack defaults.

Profile creation and updates use the same validation, so a profile cannot store a
language/level/locale combination that does not exist in the curriculum.

## Advanced feature focus

Tutor chat accepts an optional `features` list:

```json
{
  "profile_id": 1,
  "message": "Quiero practicar ser y estar.",
  "language": "es",
  "level": "A1",
  "locale": "es_MX",
  "features": ["ser_estar", "formality"]
}
```

Feature ids must exist for the selected language and level. The prompt builder
injects the feature names, categories, descriptions, examples, language
script/direction, and teaching notes. Selected features are marked as the
session focus so the model prioritizes them without turning every turn into a
grammar lecture.

`GET /api/v1/tutor/quick-chat` accepts `features` as a comma-separated query
parameter for constrained clients.

## Speech

Speech endpoints are local-only and optional. Install the `speech` extra and
download the Piper voices described in the project README. Text-only tutoring
continues to work when either runtime is unavailable.

| Endpoint | Request | Response |
| --- | --- | --- |
| `GET /api/v1/speech/status` | — | `stt_available`, `tts_available`, `stt_model`, `tts_voice_dir` |
| `POST /api/v1/speech/transcribe` | Multipart: `audio` file plus `language`, optional `level` and `locale` | `text`, `detected_language`, `duration`, `language`, `level`, `locale` |
| `POST /api/v1/speech/synthesize` | JSON: `text`, `language`, optional `level` and `locale` | `audio/wav` body |

Transcription accepts wav, webm, ogg, mp3, m4a, and flac uploads. The language,
level, and locale are validated against the language pack before the model is
invoked. Synthesis resolves a locale-specific Piper voice when installed and
falls back to the base language voice.

Tutor chat limits messages to 4,000 characters and history to 20 entries;
transcription rejects uploads larger than 15 MB.

```bash
curl -F "audio=@sample.webm" \
  -F "language=es" -F "level=A1" -F "locale=es_MX" \
  http://localhost:8000/api/v1/speech/transcribe

curl -X POST http://localhost:8000/api/v1/speech/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text":"Hola, ¿cómo estás?","language":"es","level":"A1","locale":"es_MX"}' \
  --output reply.wav
```

If the `speech` extra is not installed, transcription and synthesis return HTTP
503 with setup instructions. Synthesis also returns 503 when the requested
voice file is missing.
