from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

_DATA_PATH = Path(__file__).parent.parent / "data" / "compatibility.json"

_compat: dict[str, list[str]] = {}


def _ensure_loaded() -> None:
    if not _compat:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
        _compat.update({k.upper(): [p.upper() for p in v] for k, v in raw.items()})


def check_compatibility(
    model_number: str, part_number: str
) -> Literal["compatible", "not_compatible", "unknown"]:
    _ensure_loaded()
    parts = _compat.get(model_number.upper())
    if parts is None:
        return "unknown"
    return "compatible" if part_number.upper() in parts else "not_compatible"


def get_compatible_parts(model_number: str) -> list[str]:
    _ensure_loaded()
    return _compat.get(model_number.upper(), [])
