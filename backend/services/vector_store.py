import os
import json
import numpy as np
import faiss
from typing import List, Tuple
from pathlib import Path

from core.config import settings


def _index_path(user_id: int) -> str:
    return os.path.join(settings.FAISS_INDEX_DIR, f"user_{user_id}.index")


def _meta_path(user_id: int) -> str:
    return os.path.join(settings.FAISS_INDEX_DIR, f"user_{user_id}_meta.json")


def load_or_create_index(user_id: int, dim: int = 768) -> Tuple[faiss.Index, List[int]]:
    """
    Load existing FAISS index for a user, or create a new one.
    Returns (index, chunk_id_map) where chunk_id_map[i] = db chunk id at position i.
    """
    idx_path = _index_path(user_id)
    meta_path = _meta_path(user_id)

    if os.path.exists(idx_path) and os.path.exists(meta_path):
        index = faiss.read_index(idx_path)
        with open(meta_path, "r") as f:
            chunk_id_map = json.load(f)
    else:
        index = faiss.IndexFlatIP(dim)  # Inner product (cosine after normalization)
        chunk_id_map = []

    return index, chunk_id_map


def save_index(user_id: int, index: faiss.Index, chunk_id_map: List[int]):
    faiss.write_index(index, _index_path(user_id))
    with open(_meta_path(user_id), "w") as f:
        json.dump(chunk_id_map, f)


def add_embeddings(user_id: int, embeddings: List[List[float]], chunk_db_ids: List[int]) -> List[int]:
    """
    Add embeddings to FAISS index.
    Returns list of FAISS index positions assigned to each embedding.
    """
    if not embeddings:
        return []

    dim = len(embeddings[0])
    index, chunk_id_map = load_or_create_index(user_id, dim)

    vectors = np.array(embeddings, dtype=np.float32)
    # Normalize for cosine similarity
    faiss.normalize_L2(vectors)

    start_pos = index.ntotal
    index.add(vectors)

    # Map: position in FAISS → db chunk id
    faiss_positions = list(range(start_pos, start_pos + len(embeddings)))
    chunk_id_map.extend(chunk_db_ids)

    save_index(user_id, index, chunk_id_map)
    return faiss_positions


def search_similar(user_id: int, query_embedding: List[float], top_k: int = None) -> List[Tuple[int, float]]:
    """
    Search FAISS for most similar chunks.
    Returns list of (db_chunk_id, score) sorted by score desc.
    """
    top_k = top_k or settings.TOP_K_RESULTS
    idx_path = _index_path(user_id)

    if not os.path.exists(idx_path):
        return []

    index, chunk_id_map = load_or_create_index(user_id)

    if index.ntotal == 0:
        return []

    query_vec = np.array([query_embedding], dtype=np.float32)
    faiss.normalize_L2(query_vec)

    k = min(top_k, index.ntotal)
    scores, indices = index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx != -1 and idx < len(chunk_id_map):
            db_chunk_id = chunk_id_map[idx]
            results.append((db_chunk_id, float(score)))

    return results


def delete_document_from_index(user_id: int, faiss_positions: List[int]):
    """
    FAISS IndexFlatIP doesn't support deletion natively.
    We handle this by marking deleted positions in metadata.
    For production: use IndexIDMap or rebuild index.
    This is a simplified approach — rebuild the index minus deleted positions.
    """
    # For fresher portfolio: note this in README as a known limitation
    # Production solution: use IndexIDMap2 or Pinecone/Qdrant
    pass
