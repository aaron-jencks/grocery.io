from __future__ import annotations

from pathlib import Path

from db_server.db.connection import Database


class MigrationRunner:
    def __init__(self, database: Database, migrations_dir: Path):
        self.database = database
        self.migrations_dir = migrations_dir

    def apply_all(self) -> None:
        migration_files = sorted(self.migrations_dir.glob("*.sql"))
        with self.database.connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            applied = {
                row["version"]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }

            for migration_file in migration_files:
                version = migration_file.name
                if version in applied:
                    continue

                connection.executescript(migration_file.read_text())
                connection.execute(
                    "INSERT INTO schema_migrations(version) VALUES (?)",
                    (version,),
                )
