from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional

from app.tools.vector_store import async_similarity_search

_INSTALL_PATH = Path(__file__).parent.parent / "data" / "install_guides.jsonl"
_TROUBLE_PATH = Path(__file__).parent.parent / "data" / "troubleshooting_guides.jsonl"

_install_guides: List[dict] = []
_troubleshooting_guides: List[dict] = []


def _load_jsonl(path: Path) -> List[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _ensure_loaded() -> None:
    if not _install_guides:
        _install_guides.extend(_load_jsonl(_INSTALL_PATH))
    if not _troubleshooting_guides:
        _troubleshooting_guides.extend(_load_jsonl(_TROUBLE_PATH))


# ---------------------------------------------------------------------------
# Keyword-based fallbacks (used when vector index has not been built yet)
# ---------------------------------------------------------------------------

def _keyword_install(part_number: Optional[str], model_number: Optional[str]) -> List[dict]:
    _ensure_loaded()
    results = []
    for guide in _install_guides:
        if part_number and guide.get("part_number", "").upper() == part_number.upper():
            results.append(guide)
            continue
        if model_number and model_number.upper() in [
            m.upper() for m in guide.get("model_numbers", [])
        ]:
            results.append(guide)
    return results


def _keyword_troubleshoot(symptom: str, appliance_type: Optional[str]) -> List[dict]:
    _ensure_loaded()
    symptom_lower = symptom.lower()
    results = []
    for guide in _troubleshooting_guides:
        if appliance_type and guide.get("appliance", "").lower() != appliance_type.lower():
            continue
        keywords: List[str] = guide.get("keywords", [])
        if any(kw in symptom_lower for kw in keywords):
            results.append(guide)
    return results


# ---------------------------------------------------------------------------
# Public API — async to support vector search
# ---------------------------------------------------------------------------

async def find_install_guides(
    part_number: Optional[str] = None,
    model_number: Optional[str] = None,
    query: Optional[str] = None,
) -> List[dict]:
    """Return relevant install guide chunks.

    When a part number or model number is provided, keyword exact-match is
    tried first — it is authoritative for known parts. Vector search is used
    when no specific part/model is supplied or when exact-match finds nothing.
    Each returned dict has a '_source' key: 'vector' or 'keyword'.
    """
    # Exact-match first when we have a specific identifier
    if part_number or model_number:
        exact = _keyword_install(part_number, model_number)
        if exact:
            for g in exact:
                g["_source"] = "keyword"
            return exact

    # No exact match (or no identifier given) — use vector search
    search_query = " ".join(
        filter(None, [query, part_number, model_number])
    ).strip() or "install guide"
    chunks = await async_similarity_search(search_query, k=3, kind="install")
    if chunks:
        for c in chunks:
            c["_source"] = "vector"
        return chunks

    return []


async def find_troubleshooting_guides(
    symptom: str,
    appliance_type: Optional[str] = None,
) -> List[dict]:
    """Return relevant troubleshooting guide chunks.

    Tries vector similarity search first; falls back to keyword matching.
    Each returned dict has a '_source' key: 'vector' or 'keyword'.
    """
    chunks = await async_similarity_search(
        symptom, k=3, kind="troubleshooting", appliance_type=appliance_type
    )
    if chunks:
        for c in chunks:
            c["_source"] = "vector"
        return chunks

    # Fallback: keyword matching
    guides = _keyword_troubleshoot(symptom, appliance_type)
    for g in guides:
        g["_source"] = "keyword"
    return guides
