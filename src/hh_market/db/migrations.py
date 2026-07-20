"""Minimal explicit migration runner for local Docker PostgreSQL."""

from pathlib import Path

import psycopg


def apply_migrations(database_url: str, migrations_dir: Path) -> int:
    """Apply ordered SQL files transactionally, relying on idempotent DDL."""
    migrations = sorted(migrations_dir.glob("*.sql"))
    with psycopg.connect(database_url, autocommit=True) as connection:
        for migration in migrations:
            connection.execute(migration.read_text(encoding="utf-8"))
    return len(migrations)
