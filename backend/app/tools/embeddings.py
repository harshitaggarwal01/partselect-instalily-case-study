from __future__ import annotations

import httpx

from app.core.config import settings


class EmbeddingError(Exception):
    pass


async def embed_texts(texts: list) -> list:
    """Return one embedding vector (list[float]) per input text.

    Dispatches to the configured provider. Currently supports 'voyage'.
    Raises EmbeddingError on network or provider errors.
    """
    provider = settings.embedding_provider.lower()

    if provider == "voyage":
        return await _embed_voyage(texts)

    raise ValueError(
        f"Unknown embedding provider '{provider}'. "
        "Set EMBEDDING_PROVIDER=voyage in your .env file."
    )


async def _embed_voyage(texts: list) -> list:
    """Call Voyage AI embeddings REST API directly."""
    api_key = settings.embedding_api_key
    model = settings.embedding_model

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.voyageai.com/v1/embeddings",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={"input": texts, "model": model},
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]
    except httpx.HTTPStatusError as exc:
        raise EmbeddingError(
            f"Voyage AI API error {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except Exception as exc:
        raise EmbeddingError(f"Voyage AI embedding failed: {exc}") from exc
