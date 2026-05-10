from __future__ import annotations

import json
from pathlib import Path

_INSTALL_PATH = Path(__file__).parent.parent / "data" / "install_guides.jsonl"
_TROUBLE_PATH = Path(__file__).parent.parent / "data" / "troubleshooting_guides.jsonl"

_install_guides: list[dict] = []
_troubleshooting_guides: list[dict] = []


def _load_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _ensure_loaded() -> None:
    if not _install_guides:
        _install_guides.extend(_load_jsonl(_INSTALL_PATH))
    if not _troubleshooting_guides:
        _troubleshooting_guides.extend(_load_jsonl(_TROUBLE_PATH))


def find_install_guides(
    part_number: str | None = None, model_number: str | None = None
) -> list[dict]:
    _ensure_loaded()
    results = []
    for guide in _install_guides:
        if part_number and guide.get("part_number", "").upper() == part_number.upper():
            results.append(guide)
            continue
        if model_number and model_number.upper() in [m.upper() for m in guide.get("model_numbers", [])]:
            results.append(guide)
    return results


def find_troubleshooting_guides(
    symptom: str, appliance_type: str | None = None
) -> list[dict]:
    _ensure_loaded()
    symptom_lower = symptom.lower()
    results = []
    for guide in _troubleshooting_guides:
        if appliance_type and guide.get("appliance", "").lower() != appliance_type.lower():
            continue
        keywords: list[str] = guide.get("keywords", [])
        if any(kw in symptom_lower for kw in keywords):
            results.append(guide)
    return results
