#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

HOST="${GROCERY_DB_HOST:-0.0.0.0}"
PORT="${GROCERY_DB_PORT:-50051}"
DB_PATH="${GROCERY_DB_PATH:-${PROJECT_ROOT}/db_server/data/grocery.db}"
PYTHON_BIN="${GROCERY_DB_PYTHON:-${PROJECT_ROOT}/db_server/.venv/bin/python}"

mkdir -p "$(dirname "${DB_PATH}")"

cd "${PROJECT_ROOT}"
exec "${PYTHON_BIN}" -m db_server.main --host "${HOST}" --port "${PORT}" --db-path "${DB_PATH}"
