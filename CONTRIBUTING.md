# Contributing to Polyglot Coach

Welcome, and thank you for your interest in contributing to Polyglot Coach.
This project focuses on local-first, offline-capable language learning powered by open models.

## Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv)
- Node 20+ and [pnpm](https://pnpm.io/) only when working on packaged frontend
  code; the current web client is static and served by FastAPI

## Setup

```bash
git clone https://github.com/Castle96/polyglot-coach.git
cd polyglot-coach
uv sync
```

`pnpm install` is not required for the current static web client. The workspace
scripts will become relevant once `apps/web` and `apps/desktop` contain their
own `package.json` files.

## Project Structure Overview

- `apps/` contains the desktop, web, and API application entry points.
- `mcp/` contains Python MCP services using a `src/` layout.
- `profiles/` stores language profile configuration files.
- `curriculum/` stores the registry, language packs, and level-based content.
- `datasets/` stores structured vocabulary, grammar, and example datasets.
- `models/` documents local model assets and the Piper voice manifest.
- `storage/` contains SQLite data files and migration assets.
- `docs/` contains architecture, curriculum, MCP, and API documentation.
- `tools/` contains curriculum validation, generation, and voice download scripts.

## Running MCP Services Locally

Each MCP service is a standalone Python package inside `mcp/`.
After running `uv sync`, enter a service directory and use your preferred MCP runner
or Python entrypoint conventions as the implementation is added.

## Code Style

- Python code should be formatted and linted with Ruff.
- JavaScript and TypeScript code should use strict TypeScript mode once the apps are implemented.
- Keep changes aligned with the local-first, language-learning-focused vision of the project.

## Testing

- Use `pytest` for Python MCP services.
- Validate curriculum changes with `uv run python tools/validate_curriculum.py`.
- Add JavaScript or TypeScript tests alongside the relevant apps as packaged
  frontend code is introduced.
- Run the full repository checks before opening a pull request:
  `uv run python tools/validate_curriculum.py && uv run pytest`.

## Adding a Language

Add a language pack under `curriculum/<iso-code>/`, enable it in
`curriculum/registry.yaml`, and add voice assets to
`models/tts/voices.yaml` when TTS is supported. Do not list a level or language
as supported until its content exists and the validator passes. See
[docs/curriculum/README.md](docs/curriculum/README.md) for the schema.

## Branch Naming Conventions

- `feature/<short-description>`
- `fix/<short-description>`
- `docs/<short-description>`
- `chore/<short-description>`

## Pull Request Guidelines

- Keep pull requests focused and scoped to a single change.
- Update documentation whenever repository structure or developer workflows change.
- Include tests or validation notes for functional changes.
- Ensure proposed changes remain compatible with offline, local-first operation.

For architecture guidance, see [docs/architecture/README.md](docs/architecture/README.md).
