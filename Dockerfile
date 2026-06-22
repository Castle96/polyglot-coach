services:
  polyglot-coach:
    build: .
    container_name: polyglot-coach
    ports:
      - "8004:8000"
    extra_hosts:
      - "host.docker.internal:host-gateway"
    volumes:
      - .:/app
      - /app/.venv
      - ./storage:/app/storage
      - ./profiles:/app/profiles
      - ./curriculum:/app/curriculum
    environment:
      TZ: America/Chicago
      OLLAMA_HOST: http://host.docker.internal:11434
      PYTHONPATH: /app
    working_dir: /app
    command: uv run uvicorn apps.api.main:app --host 0.0.0.0 --port 8004 --reload
