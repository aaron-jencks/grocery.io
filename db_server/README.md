# db_server

Minimal backend skeleton for the grocery gRPC server.

## Layout

- `db/connection.py`: SQLite connection management
- `db/migrations.py`: applies versioned SQL migrations
- `db/migrations/`: schema files
- `repositories/grocery.py`: database access for UPC lookup and price observations
- `domain/`: simple domain dataclasses

## Migration Model

Migrations live in `db/migrations/` as plain `.sql` files.

Naming:

- Use a sortable prefix so files run in the intended order.
- The current code sorts by filename, so lexicographic order is the migration order.
- A simple convention is `001_init.sql`, `002_add_indexes.sql`, `003_add_users.sql`.

What a migration should contain:

- Normal SQLite DDL and data backfill SQL.
- Usually `CREATE TABLE`, `ALTER TABLE`, `CREATE INDEX`, and optional `UPDATE` statements.
- Keep each file idempotent when practical, for example `CREATE TABLE IF NOT EXISTS`.

What the runner does:

- On startup, `create_database(...)` calls `MigrationRunner.apply_all()`.
- The runner creates a `schema_migrations` table if it does not already exist.
- Each migration filename is treated as its version key.
- If a filename is already present in `schema_migrations`, that file is skipped.
- If it has not been applied yet, the runner executes the full SQL file with `executescript(...)` and then records the filename in `schema_migrations`.

Important behavior:

- Renaming an already-applied migration file makes it look like a new migration.
- Editing an already-applied migration file does not re-run it automatically.
- After a migration is applied in a real environment, add a new migration instead of changing the old one.

## Usage

Create and migrate the database:

```python
from pathlib import Path

from db.bootstrap import create_database
from repositories import GroceryRepository

database = create_database(Path("data/grocery.db"))
repository = GroceryRepository(database)
```

Example migration:

```sql
CREATE TABLE IF NOT EXISTS users (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email
    ON users(email);
```

## Systemd

Repo-local unit files live in [`deploy/systemd`](/workspace/github/grocery.io/deploy/systemd).

Files:

- `grocery-db-server.service`: runs the local Python gRPC server
- `grocery-db-tunnel.service`: creates the reverse `autossh` tunnel to the EC2 forwarder
- `grocery-db.env.example`: environment variables consumed by both services

The setup mirrors the existing Plex tunnel pattern on this machine:

- local service runs on `localhost:${GROCERY_DB_PORT}`
- tunnel service publishes that port remotely with `ssh -R`

Install steps:

1. Copy the env template and fill in values:

```bash
sudo cp /workspace/github/grocery.io/deploy/systemd/grocery-db.env.example /etc/default/grocery-db
sudoedit /etc/default/grocery-db
```

2. Copy the unit files into `systemd`:

```bash
sudo cp /workspace/github/grocery.io/deploy/systemd/grocery-db-server.service /etc/systemd/system/
sudo cp /workspace/github/grocery.io/deploy/systemd/grocery-db-tunnel.service /etc/systemd/system/
```

3. Reload and enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now grocery-db-server.service
sudo systemctl enable --now grocery-db-tunnel.service
```

4. Check logs:

```bash
sudo systemctl status grocery-db-server.service
sudo systemctl status grocery-db-tunnel.service
journalctl -u grocery-db-server.service -f
journalctl -u grocery-db-tunnel.service -f
```

Notes:

- `grocery-db-server.service` runs as user `aaron`, not `root`.
- `grocery-db-tunnel.service` runs as `root`, matching the existing Plex tunnel units.
- If you do not want the remote tunnel yet, only enable `grocery-db-server.service`.
- The local launcher script is [`db_server/run_server.sh`](/workspace/github/grocery.io/db_server/run_server.sh).

## Next steps

- Wire `server.py` to the repository
- Map gRPC request messages into `PriceObservationInput`
- Add request validation and gRPC error handling
