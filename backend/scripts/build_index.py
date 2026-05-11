"""Offline index builder — run once to generate vector_index.json.

Usage:
    cd backend
    PYTHONPATH=. .venv/Scripts/python scripts/build_index.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure 'backend/' is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.embeddings import embed_texts  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
INSTALL_PATH = DATA_DIR / "install_guides.jsonl"
TROUBLE_PATH = DATA_DIR / "troubleshooting_guides.jsonl"
OUTPUT_PATH = DATA_DIR / "vector_index.json"


def _load_jsonl(path: Path) -> list:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def _chunk_install(guide: dict) -> dict:
    """Build one text chunk representing an install guide."""
    title = guide.get("title", "")
    steps_text = " ".join(
        s.get("instruction", "") for s in guide.get("steps", [])
    )
    return {
        "id": f"{guide['id']}#chunk-0",
        "guide_id": guide["id"],
        "kind": "install",
        "appliance_type": "mixed",
        "text": f"{title}. {steps_text}",
        "url": guide.get("url", ""),
    }


def _chunk_troubleshoot(guide: dict) -> dict:
    """Build one text chunk representing a troubleshooting guide."""
    symptom = guide.get("symptom", "")
    steps_text = " ".join(
        s.get("description", "") for s in guide.get("steps", [])
    )
    return {
        "id": f"{guide['id']}#chunk-0",
        "guide_id": guide["id"],
        "kind": "troubleshooting",
        "appliance_type": guide.get("appliance", "mixed"),
        "text": f"{symptom}. {steps_text}",
        "url": guide.get("url", ""),
    }


async def build() -> None:
    install_guides = _load_jsonl(INSTALL_PATH)
    trouble_guides = _load_jsonl(TROUBLE_PATH)

    chunks = []
    for g in install_guides:
        chunks.append(_chunk_install(g))
    for g in trouble_guides:
        chunks.append(_chunk_troubleshoot(g))

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
