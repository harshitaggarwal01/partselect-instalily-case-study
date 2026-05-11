"""Offline index builder — run once to generate vector_index.json.

Usage:
    cd backend
    PYTHONPATH=. .venv/Scripts/python scripts/build_index.py
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import List

# Ensure 'backend/' is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.embeddings import embed_texts  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
INSTALL_PATH = DATA_DIR / "install_guides.jsonl"
TROUBLE_PATH = DATA_DIR / "troubleshooting_guides.jsonl"
OUTPUT_PATH = DATA_DIR / "vector_index.json"

_STOPWORDS = frozenset(
    {"the", "a", "an", "is", "are", "my", "it", "in", "to", "of", "and", "not", "does", "how", "do", "i"}
)

_PART_RE = re.compile(r"\b(PS\d+|WP[A-Z0-9]+|W[0-9]{5,}[A-Z0-9]*)\b", re.I)


def _extract_keywords(text: str) -> List[str]:
    """Extract up to 5 non-stopword alphanumeric tokens longer than 3 chars."""
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    seen: list = []
    for tok in tokens:
        if len(tok) > 3 and tok not in _STOPWORDS and tok not in seen:
            seen.append(tok)
        if len(seen) >= 5:
            break
    return seen


def _extract_part_numbers(text: str) -> List[str]:
    """Extract part numbers matching PartSelect patterns."""
    return list({m.upper() for m in _PART_RE.findall(text)})


def _infer_appliance_type(text: str) -> str:
    """Infer appliance type from title/url text."""
    lower = text.lower()
    if any(k in lower for k in ("refrigerator", "fridge", "ice", "freezer")):
        return "refrigerator"
    if "dishwasher" in lower:
        return "dishwasher"
    return "mixed"


def _load_jsonl(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _chunk_install(guide: dict) -> List[dict]:
    """Build multi-chunk list for an install guide."""
    guide_id = guide["id"]
    title = guide.get("title", "")
    url = guide.get("url", "")
    steps = guide.get("steps", [])
    appliance_type = _infer_appliance_type(f"{title} {url}")

    chunks: List[dict] = []

    # --- Chunk 0: summary ---
    summary_parts = [title]
    if len(steps) >= 1:
        summary_parts.append(steps[0].get("instruction", ""))
    if len(steps) >= 2:
        summary_parts.append(steps[1].get("instruction", ""))
    summary_text = " ".join(p for p in summary_parts if p)

    chunks.append({
        "id": f"{guide_id}#summary",
        "guide_id": guide_id,
        "kind": "install",
        "appliance_type": appliance_type,
        "text": summary_text,
        "url": url,
        "step_range": "summary",
        "symptom_keywords": _extract_keywords(summary_text),
        "part_numbers": _extract_part_numbers(
            summary_text + " " + " ".join(s.get("instruction", "") for s in steps)
        ),
    })

    # --- Chunks 1..N: step groups of 2-3 ---
    group_size = 3
    for start_idx in range(0, len(steps), group_size):
        group = steps[start_idx: start_idx + group_size]
        text = " ".join(s.get("instruction", "") for s in group if s.get("instruction"))
        if not text:
            continue
        step_nums = [s.get("step_number", start_idx + i + 1) for i, s in enumerate(group)]
        step_range = f"{step_nums[0]}-{step_nums[-1]}" if len(step_nums) > 1 else str(step_nums[0])
        chunks.append({
            "id": f"{guide_id}#steps-{step_range}",
            "guide_id": guide_id,
            "kind": "install",
            "appliance_type": appliance_type,
            "text": text,
            "url": url,
            "step_range": step_range,
            "symptom_keywords": _extract_keywords(text),
            "part_numbers": _extract_part_numbers(text),
        })

    return chunks


def _chunk_troubleshoot(guide: dict) -> List[dict]:
    """Build multi-chunk list for a troubleshooting guide."""
    guide_id = guide["id"]
    symptom = guide.get("symptom", "")
    url = guide.get("url", "")
    steps = guide.get("steps", [])
    appliance_type = guide.get("appliance", "mixed")

    chunks: List[dict] = []

    # --- Chunk 0: summary (symptom sentence) ---
    summary_text = symptom
    all_steps_text = " ".join(s.get("description", "") for s in steps)

    chunks.append({
        "id": f"{guide_id}#summary",
        "guide_id": guide_id,
        "kind": "troubleshooting",
        "appliance_type": appliance_type,
        "text": summary_text,
        "url": url,
        "step_range": "summary",
        "symptom_keywords": _extract_keywords(summary_text),
        "part_numbers": _extract_part_numbers(summary_text + " " + all_steps_text),
    })

    # --- Chunks 1..N: step groups of 2-3 ---
    group_size = 3
    for start_idx in range(0, len(steps), group_size):
        group = steps[start_idx: start_idx + group_size]
        text = " ".join(s.get("description", "") for s in group if s.get("description"))
        if not text:
            continue
        step_nums = [s.get("step_number", start_idx + i + 1) for i, s in enumerate(group)]
        step_range = f"{step_nums[0]}-{step_nums[-1]}" if len(step_nums) > 1 else str(step_nums[0])
        chunks.append({
            "id": f"{guide_id}#steps-{step_range}",
            "guide_id": guide_id,
            "kind": "troubleshooting",
            "appliance_type": appliance_type,
            "text": text,
            "url": url,
            "step_range": step_range,
            "symptom_keywords": _extract_keywords(text),
            "part_numbers": _extract_part_numbers(text),
        })

    return chunks


async def build() -> None:
    install_guides = _load_jsonl(INSTALL_PATH)
    trouble_guides = _load_jsonl(TROUBLE_PATH)

    chunks: List[dict] = []
    for g in install_guides:
        chunks.extend(_chunk_install(g))
    for g in trouble_guides:
        chunks.extend(_chunk_troubleshoot(g))

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks via Voyage AI …")
    embeddings = await embed_texts(texts)

    for chunk, emb in zip(chunks, embeddings):
        chunk["embedding"] = emb

    OUTPUT_PATH.write_text(
        json.dumps(chunks, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(chunks)} entries → {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(build())
