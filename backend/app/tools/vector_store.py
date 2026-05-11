from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np

from app.tools.embeddings import embed_texts

logger = logging.getLogger("partselect_agent.vector_store")

_INDEX_PATH = Path(__file__).parent.parent / "data" / "vector_index.json"

_index: List[dict] = []
_embeddings: Optional[np.ndarray] = None


def _ensure_loaded() -> bool:
    """Load index from disk. Returns False if the file doesn't exist yet."""
    global _embeddings
    if _index:
        return True
    if not _INDEX_PATH.exists():
        logger.info("vector_store: index file not found at %s", _INDEX_PATH)
        return False
    logger.info("vector_store: loading index from %s", _INDEX_PATH)
    raw = json.loads(_INDEX_PATH.read_text(encoding="utf-8"))
    _index.extend(raw)
    _embeddings = np.array([entry["embedding"] for entry in _index], dtype=np.float32)
    logger.info("vector_store: loaded %d chunks", len(_index))
    return True


def _cosine_scores(query_vec: np.ndarray, corpus: np.ndarray) -> np.ndarray:
    """Return cosine similarity between query_vec and every row in corpus."""
    q = query_vec / (np.linalg.norm(query_vec) + 1e-10)
    norms = np.linalg.norm(corpus, axis=1, keepdims=True) + 1e-10
    normed = corpus / norms
    return normed @ q


async def async_similarity_search(
    query: str,
    k: int = 6,
    appliance_type: Optional[str] = None,
    kind: Optional[str] = None,
    symptom_keyword: Optional[str] = None,
    part_number: Optional[str] = None,
) -> List[dict]:
    """Embed query then return the top-k most similar chunks.

    Returns empty list if the vector index hasn't been built yet (graceful fallback).

    Optional metadata boosts (applied before sorting):
    - symptom_keyword: multiply score by 1.2 if chunk's symptom_keywords contains it
    - part_number: multiply score by 1.3 if chunk's part_numbers contains it
    """
    if not _ensure_loaded():
        return []

    # Filter candidate indices
    candidates = [
        i for i, entry in enumerate(_index)
        if (kind is None or entry.get("kind") == kind)
        and (
            appliance_type is None
            or entry.get("appliance_type") in (appliance_type, "mixed")
        )
    ]
    if not candidates:
        return []

    query_emb_list = await embed_texts([query])
    query_vec = np.array(query_emb_list[0], dtype=np.float32)

    candidate_matrix = _embeddings[candidates]  # type: ignore[index]
    scores = _cosine_scores(query_vec, candidate_matrix)

    # Apply metadata boosts before sorting
    symptom_kw_lower = symptom_keyword.lower() if symptom_keyword else None
    part_num_lower = part_number.lower() if part_number else None

    for local_idx, global_idx in enumerate(candidates):
        entry = _index[global_idx]
        if symptom_kw_lower is not None:
            kw_list = [kw.lower() for kw in entry.get("symptom_keywords", [])]
            if symptom_kw_lower in kw_list:
                scores[local_idx] *= 1.2
        if part_num_lower is not None:
            pn_list = [pn.lower() for pn in entry.get("part_numbers", [])]
            if part_num_lower in pn_list:
                scores[local_idx] *= 1.3

    # Sort by descending score and take top-k
    top_local = int(min(k, len(candidates)))
    top_indices = np.argsort(scores)[::-1][:top_local]

    results = []
    for local_idx in top_indices:
        global_idx = candidates[local_idx]
        entry = dict(_index[global_idx])
        entry["score"] = float(scores[local_idx])
        entry.pop("embedding", None)  # don't return raw vector to callers
        results.append(entry)

    return results
