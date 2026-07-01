from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def load_config(config_path: str | Path) -> dict[str, Any]:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    if "data" not in cfg:
        raise ValueError("Config must contain a 'data' section.")
    if "file" not in cfg["data"]:
        raise ValueError("Config data section must contain 'file'.")

    return cfg


def resolve_path(config_path: str | Path, possibly_relative_path: str | Path) -> Path:
    p = Path(possibly_relative_path)
    if p.is_absolute():
        return p
    return Path(config_path).parent.parent / p
