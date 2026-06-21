import os
import uuid
import asyncio
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.database import get_db
from models.models import User, Document, DocumentChunk
from core.security import get_current_user
from core.config import settings
from services.document_processor import process_document, get_file_type
from services.embeddings import get_embeddings_batch
from services.vector_store import add_embeddings

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentResponse(BaseModel):
    id: int
    original_name: str
    file_type: str
    file_size: int
    chunk_count: int
    status: str
    created_at: str

    class Config:
        from_attributes = True


async def process_and_index_document(doc_id: int, file_path: str, file_type: str, user_id: int, db: Session):
    """Background task: parse → chunk → embed → index."""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        return

    try:
        # 1. Parse and chunk
        chunks = process_document(file_path, file_type)

        # 2. Save chunks to DB
        db_chunks = []
        for chunk_data in chunks:
            db_chunk = DocumentChunk(
                document_id=doc_id,
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                page_number=chunk_data["page_number"]
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        db.commit()
        for c in db_chunks:
            db.refresh(c)

        # 3. Generate embeddings
        texts = [c.content for c in db_chunks]
        embeddings = await get_embeddings_batch(texts)

        # 4. Add to FAISS
        chunk_db_ids = [c.id for c in db_chunks]
        faiss_positions = add_embeddings(user_id, embeddings, chunk_db_ids)

        # 5. Update faiss_index_id on each chunk
        for chunk, pos in zip(db_chunks, faiss_positions):
            chunk.faiss_index_id = pos

        doc.chunk_count = len(db_chunks)
        doc.status = "ready"
        db.commit()

    except Exception as e:
        doc.status = "failed"
        db.commit()
        print(f"[ERROR] Processing doc {doc_id}: {e}")


@router.post("/upload", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate file type
    try:
        file_type = get_file_type(file.filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, and CSV files are supported.")

    # Save file to disk
    unique_name = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_name)

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    doc = Document(
        filename=unique_name,
        original_name=file.filename,
        file_type=file_type,
        file_size=len(content),
        status="processing",
        user_id=current_user.id
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process in background
    background_tasks.add_task(
        process_and_index_document, doc.id, file_path, file_type, current_user.id, db
    )

    return {"message": "File uploaded. Processing in background.", "document_id": doc.id}


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    docs = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        DocumentResponse(
            id=d.id,
            original_name=d.original_name,
            file_type=d.file_type,
            file_size=d.file_size or 0,
            chunk_count=d.chunk_count or 0,
            status=d.status,
            created_at=str(d.created_at)
        )
        for d in docs
    ]


@router.get("/{doc_id}")
def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete file from disk
    file_path = os.path.join(settings.UPLOAD_DIR, doc.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    db.delete(doc)
    db.commit()
