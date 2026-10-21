# SQLite Storage

This directory is the default location for SQLite database files used by
Polyglot Coach. Database files ending in `.db` and `.sqlite` are ignored by git.

## Configuration

Set `POLYGLOT_DB_PATH` to choose the database file. `run.sh`, Docker Compose,
and the Kubernetes manifest set it to a persistent path. Without it, the
application defaults to `~/.polyglot-coach/data.db`.

Tables are currently created with SQLAlchemy's `create_all` at startup. Alembic
migrations are not wired up yet; see `storage/migrations/README.md`.
