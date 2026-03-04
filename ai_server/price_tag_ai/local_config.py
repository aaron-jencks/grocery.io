from __future__ import annotations

import json
import os
from pathlib import Path


def load_local_secrets(base_dir: str | Path) -> dict[str, str]:
    path = Path(base_dir) / "local.secrets.json"
    if not path.exists():
        return {}

    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        raise ValueError("local.secrets.json must contain a JSON object")

    return {
        str(key): str(value)
        for key, value in payload.items()
        if value is not None
    }


def resolve_openai_api_key(base_dir: str | Path) -> str | None:
    return os.environ.get("OPENAI_API_KEY") or load_local_secrets(base_dir).get("openai_api_key")


def resolve_openai_model(base_dir: str | Path) -> str | None:
    return os.environ.get("OPENAI_MODEL") or load_local_secrets(base_dir).get("openai_model")
