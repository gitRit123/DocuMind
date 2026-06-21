import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from models.models import User, ChatMessage
from core.security import get_current_user
from services.rag_pipeline import run_rag_pipeline

router = APIRouter(prefix="/chat", tags=["chat"])


class QueryRequest(BaseModel):
    question: str


class SourceItem(BaseModel):
    filename: str
    page_number: int | None
    excerpt: str
    relevance_score: float


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceItem]
    question: str


class ChatHistoryItem(BaseModel):
    id: int
    role: str
    content: str
    sources: List[dict] | None
    created_at: str


@router.post("/query", response_model=QueryResponse)
async def query(
    req: QueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Run RAG pipeline
    result = await run_rag_pipeline(current_user.id, req.question, db)

    # Save to chat history
    user_msg = ChatMessage(
        user_id=current_user.id,
        role="user",
        content=req.question
    )
    assistant_msg = ChatMessage(
        user_id=current_user.id,
        role="assistant",
        content=result["answer"],
        sources=json.dumps(result["sources"])
    )
    db.add(user_msg)
    db.add(assistant_msg)
    db.commit()

    return QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        question=req.question
    )


@router.get("/history", response_model=List[ChatHistoryItem])
def get_history(
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
        .all()
    )

    return [
        ChatHistoryItem(
            id=m.id,
            role=m.role,
            content=m.content,
            sources=json.loads(m.sources) if m.sources else None,
            created_at=str(m.created_at)
        )
        for m in reversed(messages)
    ]


@router.delete("/history", status_code=204)
def clear_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    db.query(ChatMessage).filter(ChatMessage.user_id == current_user.id).delete()
    db.commit()
