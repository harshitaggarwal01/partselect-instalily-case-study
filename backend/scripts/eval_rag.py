"""RAG evaluation script.

Usage:
    cd backend
    PYTHONPATH=. .venv/Scripts/python scripts/eval_rag.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Ensure 'backend/' is on sys.path when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.tools.vector_store import async_similarity_search  # noqa: E402

DATA_DIR = Path(__file__).parent.parent / "app" / "data"
EVAL_PATH = DATA_DIR / "rag_eval_queries.json"


async def main() -> None:
    queries = json.loads(EVAL_PATH.read_text(encoding="utf-8"))

    passed = 0
    total = len(queries)

    for q in queries:
        qid = q["id"]
        query_text = q["query"]
        kind = q.get("kind")
        appliance_type = q.get("appliance_type")
        expected_ids = set(q.get("expected_guide_ids", []))

        results = await async_similarity_search(
            query_text,
            k=6,
            kind=kind,
            appliance_type=appliance_type,
        )

        # Check top-3 guide_ids against expected
        top3_guide_ids = {r.get("guide_id") for r in results[:3]}
        hit = bool(expected_ids & top3_guide_ids)

        status = "PASS" if hit else "FAIL"
        if hit:
            passed += 1

        print(
            f"[{status}] {qid}: '{query_text}'\n"
            f"       expected={sorted(expected_ids)}  "
            f"got top-3 guide_ids={sorted(top3_guide_ids)}"
        )

    recall_at_3 = passed / total if total > 0 else 0.0
    print(f"\n--- Results ---")
    print(f"Passed: {passed}/{total}")
    print(f"Recall@3: {recall_at_3:.2%}")


if __name__ == "__main__":
    asyncio.run(main())
