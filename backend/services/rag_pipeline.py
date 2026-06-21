import json
import httpx
from typing import List, Tuple
from sqlalchemy.orm import Session

from core.config import settings
from models.models import DocumentChunk, Document
from services.embeddings import get_embedding
from services.vector_store import search_similar


async def retrieve_relevant_chunks(
    user_id: int,
    query: str,
    db: Session,
    top_k: int = None
) -> List[dict]:
    """
    Embed query → search FAISS → fetch chunk content from DB.
    Returns list of {content, filename, page_number, score}
    """
    top_k = top_k or settings.TOP_K_RESULTS

    # 1. Embed the query
    query_embedding = await get_embedding(query)

    # 2. Search vector store
    results = search_similar(user_id, query_embedding, top_k)

    if not results:
        return []

    # 3. Fetch chunk details from DB
    chunk_ids = [chunk_id for chunk_id, _ in results]
    score_map = {chunk_id: score for chunk_id, score in results}

    chunks = db.query(DocumentChunk).filter(DocumentChunk.id.in_(chunk_ids)).all()

    # 4. Enrich with document filename
    doc_ids = list({c.document_id for c in chunks})
    docs = db.query(Document).filter(Document.id.in_(doc_ids)).all()
    doc_map = {d.id: d.original_name for d in docs}

    enriched = []
    for chunk in chunks:
        enriched.append({
            "chunk_id": chunk.id,
            "content": chunk.content,
            "filename": doc_map.get(chunk.document_id, "Unknown"),
            "page_number": chunk.page_number,
            "score": score_map.get(chunk.id, 0.0)
        })

    # Sort by score descending
    enriched.sort(key=lambda x: x["score"], reverse=True)
    return enriched


def build_prompt(query: str, context_chunks: List[dict]) -> str:
    """Build RAG prompt with retrieved context."""
    context_text = ""
    for i, chunk in enumerate(context_chunks, 1):
        context_text += f"\n[Source {i}: {chunk['filename']}, Page {chunk['page_number']}]\n{chunk['content']}\n"

    prompt = f"""You are DocuMind, an AI assistant that answers questions based on the provided document context.

CONTEXT:
{context_text}

QUESTION: {query}

INSTRUCTIONS:
- Answer based ONLY on the provided context.
- If the answer is not in the context, say "I couldn't find relevant information in the uploaded documents."
- Always mention which source(s) your answer comes from.
- Be concise and accurate.

ANSWER:"""
    return prompt


async def generate_answer(prompt: str) -> str:
    """Call Ollama LLM to generate an answer."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": settings.OLLAMA_LLM_MODEL,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["response"].strip()


async def run_rag_pipeline(
    user_id: int,
    query: str,
    db: Session
) -> dict:
    """
    Full RAG pipeline:
    1. Retrieve relevant chunks
    2. Build prompt
    3. Generate answer
    4. Return answer + sources
    """
    # Step 1: Retrieve
    relevant_chunks = await retrieve_relevant_chunks(user_id, query, db)

    if not relevant_chunks:
        return {
            "answer": "No documents found. Please upload some documents first.",
            "sources": []
        }

    # Step 2: Build prompt
    prompt = build_prompt(query, relevant_chunks)

    # Step 3: Generate
    answer = await generate_answer(prompt)

    # Step 4: Format sources
    sources = [
        {
            "filename": c["filename"],
            "page_number": c["page_number"],
            "excerpt": c["content"][:200] + "..." if len(c["content"]) > 200 else c["content"],
            "relevance_score": round(c["score"], 4)
        }
        for c in relevant_chunks
    ]

    return {
        "answer": answer,
        "sources": sources
    }
