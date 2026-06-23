FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=apps/api/pyproject.toml,target=apps/api/pyproject.toml \
    --mount=type=bind,source=mcp/shared/pyproject.toml,target=mcp/shared/pyproject.toml \
    --mount=type=bind,source=mcp/learner-memory/pyproject.toml,target=mcp/learner-memory/pyproject.toml \
    --mount=type=bind,source=mcp/curriculum/pyproject.toml,target=mcp/curriculum/pyproject.toml \
    --mount=type=bind,source=mcp/dictionary/pyproject.toml,target=mcp/dictionary/pyproject.toml \
    --mount=type=bind,source=mcp/grammar/pyproject.toml,target=mcp/grammar/pyproject.toml \
    --mount=type=bind,source=mcp/locale/pyproject.toml,target=mcp/locale/pyproject.toml \
    --mount=type=bind,source=mcp/conversation/pyproject.toml,target=mcp/conversation/pyproject.toml \
    --mount=type=bind,source=mcp/review/pyproject.toml,target=mcp/review/pyproject.toml \
    --mount=type=bind,source=mcp/analytics/pyproject.toml,target=mcp/analytics/pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

COPY pyproject.toml uv.lock ./
COPY apps apps
COPY mcp mcp

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

EXPOSE 8000

CMD ["uv", "run", "--no-dev", "uvicorn", "polyglot_coach_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
