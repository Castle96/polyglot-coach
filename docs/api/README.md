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
- `/health` — database, LLM provider/model, STT/TTS, and curriculum status
- `/readyz` — readiness probe; 503 unless the database and registry are usable

Health and readiness checks never download or provision models. The configured
Ollama model is pulled by `./run.sh` (or explicitly with `ollama pull`) so probes
cannot trigger a multi-gigabyte download.

## LLM providers

The tutor supports three backend families: local Ollama, local GGUF via
llama-cpp-python, and any OpenAI-compatible chat completions API. Provider
selection is server-side by default, with optional per-request credentials for
bring-your-own-key clients. The OpenAI-compatible client uses Bearer
authentication and `POST {base_url}/chat/completions`; providers that require a
different auth header or deployment-specific URL scheme need an adapter.

### Server configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `POLYGLOT_LLM_PROVIDER` | `auto` | `auto`, `openai`, `ollama`, or `llama-cpp` |
| `POLYGLOT_OPENAI_API_KEY` | — | API key for `auto` and `openai` |
| `POLYGLOT_OPENAI_BASE_URL` | `https://api.openai.com/v1` | API root; `/v1` is appended when missing |
| `POLYGLOT_OPENAI_MODEL` | `gpt-4o-mini` | Provider-specific model id |
| `POLYGLOT_OPENAI_TIMEOUT` | `90` | Request timeout in seconds |

`auto` chooses OpenAI-compatible when `POLYGLOT_OPENAI_API_KEY` is present, then
Ollama when the configured model is available, then llama-cpp. The generic
`OPENAI_API_KEY` environment variable is accepted only when
`POLYGLOT_LLM_PROVIDER=openai`; it is deliberately ignored by `auto` to avoid
unexpected cloud charges.

An explicit provider that is misconfigured does not silently fall back. For
example, `POLYGLOT_LLM_PROVIDER=openai` without a key reports `llm_available:
false` and chat returns HTTP 503 until the key is supplied.

### Per-request keys (BYOK)

Clients can supply their own provider settings on `POST /api/v1/tutor/chat` and
`GET /api/v1/tutor/quick-chat`:

| Header | Required with | Meaning |
| --- | --- | --- |
| `X-Polyglot-LLM-API-Key` | — | Enables BYOK for this request |
| `X-Polyglot-LLM-Base-URL` | API key | `http://` or `https://` API root |
| `X-Polyglot-LLM-Model` | API key | Provider model id |

When a key header is present, the OpenAI-compatible backend is used for that
request even if the server has no local model. Base URL and model fall back to
the server configuration and then to the OpenAI defaults. Supplying a URL or
model without a key returns HTTP 422. Header values are capped at 500 characters
for the key and base URL and 200 for the model; base URLs must use `http` or
`https` and must not embed credentials.

```bash
curl -X POST http://localhost:8000/api/v1/tutor/chat \
  -H "Content-Type: application/json" \
  -H "X-Polyglot-LLM-API-Key: sk-..." \
  -H "X-Polyglot-LLM-Base-URL: https://openrouter.ai/api/v1" \
  -H "X-Polyglot-LLM-Model: openai/gpt-4o-mini" \
  -d '{"profile_id":1,"message":"Hola","language":"es","level":"A1"}'
```

The bundled web client exposes these fields under **Model Provider**. It stores
the base URL and model in `localStorage` and the key in `sessionStorage`; the
server does not persist per-request keys.

### Status and errors

`GET /api/v1/tutor/status` returns the server-level provider information:

```json
{
  "llm_available": true,
  "provider": "openai",
  "model": "gpt-4o-mini",
  "base_url": "https://api.openai.com/v1",
  "byok_supported": true
}
```

`GET /health` includes `llm_available`, `llm_provider`, and `llm_model`.
Credentials are never returned by either endpoint.

Provider failures map to HTTP 502 with a short message such as
`LLM provider returned HTTP 401: invalid api key`; connection failures and
timeouts are reported the same way. Missing local/provider configuration returns
HTTP 503. Local Ollama and llama-cpp runtime failures still degrade to the
built-in fallback reply, while explicit OpenAI-compatible failures are surfaced
to the caller.

### Security notes

- Do not expose this API publicly without authentication and TLS. BYOK keys are
  sent to the server and may transit the network; the web client uses
  `sessionStorage`, but HTTPS is still required for remote deployments.
- BYOK base URLs are fetched by the API server. If the service is reachable by
  untrusted users, restrict egress or place it behind an authenticated proxy to
  avoid server-side request forgery against internal services.
- Health, status, and error responses intentionally omit API keys. Avoid adding
  request-header logging that would capture `X-Polyglot-LLM-API-Key`.

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
