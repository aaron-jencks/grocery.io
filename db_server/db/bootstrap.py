from __future__ import annotations

from pathlib import Path

from db_server.db.connection import Database
from db_server.db.migrations import MigrationRunner


def create_database(db_path: Path) -> Database:
    database = Database(db_path)
    migrations_dir = Path(__file__).resolve().parent / "migrations"
    MigrationRunner(database, migrations_dir).apply_all()
    return database
