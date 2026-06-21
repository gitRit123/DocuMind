import os
import csv
import io
from pathlib import Path
from typing import List, Tuple

import PyPDF2
import docx
import pandas as pd

from core.config import settings


def parse_pdf(file_path: str) -> List[Tuple[str, int]]:
    """Returns list of (text, page_number)"""
    chunks = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            text = text.strip()
            if text:
                chunks.append((text, page_num))
    return chunks


def parse_docx(file_path: str) -> List[Tuple[str, int]]:
    """Returns list of (paragraph_text, paragraph_index)"""
    doc = docx.Document(file_path)
    chunks = []
    for i, para in enumerate(doc.paragraphs):
        text = para.text.strip()
        if text:
            chunks.append((text, i + 1))
    return chunks


def parse_csv(file_path: str) -> List[Tuple[str, int]]:
    """Convert CSV rows to text chunks"""
    df = pd.read_csv(file_path)
    chunks = []
    # Header as context
    header = ", ".join(df.columns.tolist())
    # Every 10 rows as one chunk
    batch_size = 10
    for i in range(0, len(df), batch_size):
        batch = df.iloc[i:i + batch_size]
        rows_text = batch.to_string(index=False)
        chunk_text = f"Columns: {header}\n{rows_text}"
        chunks.append((chunk_text, i // batch_size + 1))
    return chunks


def split_into_chunks(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """Split text into overlapping chunks"""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap  # move forward with overlap
    return chunks


def process_document(file_path: str, file_type: str) -> List[dict]:
    """
    Parse + chunk a document.
    Returns list of dicts: {content, page_number, chunk_index}
    """
    # Step 1: Parse file into raw page/paragraph blocks
    if file_type == "pdf":
        raw_blocks = parse_pdf(file_path)
    elif file_type == "docx":
        raw_blocks = parse_docx(file_path)
    elif file_type == "csv":
        raw_blocks = parse_csv(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    # Step 2: Chunk each block
    all_chunks = []
    chunk_index = 0
    for text, page_number in raw_blocks:
        sub_chunks = split_into_chunks(text)
        for sub_chunk in sub_chunks:
            all_chunks.append({
                "content": sub_chunk,
                "page_number": page_number,
                "chunk_index": chunk_index
            })
            chunk_index += 1

    return all_chunks


def get_file_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    mapping = {".pdf": "pdf", ".docx": "docx", ".csv": "csv"}
    if ext not in mapping:
        raise ValueError(f"Unsupported file extension: {ext}")
    return mapping[ext]
