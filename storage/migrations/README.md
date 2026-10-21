# Storage Migrations

This directory is reserved for Alembic migrations for the SQLite storage layer.

Alembic is not configured yet. The current schema is created by
`polyglot_coach_shared.database.init_db()` using SQLAlchemy metadata. Adding
migrations is a follow-up task; until then, schema changes require a fresh
database or a manual migration.
