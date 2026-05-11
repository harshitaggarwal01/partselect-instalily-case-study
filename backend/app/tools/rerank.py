from __future__ import annotations

import json
import logging
from typing import List

from app.llm.claude_client import MODEL_FAST, chat_claude, DOMAIN_SYSTEM_PROMPT

logger = logging.getLogger("partselect_agent.rerank")


async def rerank_chunks(question: str, chunks: List[dict], top_k: int = 3) -> List[dict]:
    """Use haiku to rerank chunks by relevance to the question.

    Sends a single prompt listing chunk snippets with indices.
    Returns top_k most relevant chunks.
    Falls back to original order if LLM call fails.
    """
    if len(chunks) <= top_k:
        return chunks

    # Build snippet list
    snippets = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")[:150]
        snippets.append(f"{i}: {text}")

    prompt = (
        f"Question: {question}\n\n"
        f"Rank these {len(chunks)} text chunks by relevance to the question above.\n"
        f"Return ONLY a JSON array of the top {top_k} indices, most relevant first.\n"
        f"Example: [2, 0, 4]\n\n"
        f"Chunks:\n" + "\n".join(snippets)
    )

    try:
        raw = await chat_claude(
            DOMAIN_SYSTEM_PROMPT,
            [{"role": "user", "content": prompt}],
            max_tokens=50,
            model=MODEL_FAST,
        )
        indices = json.loads(raw.strip())
        if isinstance(indices, list):
            valid = [i for i in indices if isinstance(i, int) and 0 <= i < len(chunks)]
            return [chunks[i] for i in valid[:top_k]]
    except Exception as e:
        logger.warning("rerank failed: %s", e)

    return chunks[:top_k]
