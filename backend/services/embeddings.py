import httpx
from typing import List
from core.config import settings


async def get_embedding(text: str) -> List[float]:
    """Get embedding vector for a single text via Ollama."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": settings.OLLAMA_EMBED_MODEL,
                "prompt": text
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


async def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Get embeddings for a list of texts."""
    embeddings = []
    for text in texts:
        embedding = await get_embedding(text)
        embeddings.append(embedding)
    return embeddings
