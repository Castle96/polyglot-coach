# API App

FastAPI bridge connecting the web client to the MCP services, SQLite,
curriculum registry, and local model runtimes.

The app also serves the static web client from `apps/web` at `/`.

## Entry point

```bash
uv run uvicorn polyglot_coach_api.main:app --host 0.0.0.0 --port 8000 --reload
```

Or use `./run.sh` from the repository root.
