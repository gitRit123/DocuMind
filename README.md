# DocuMind — Ask Your Documents Anything

A RAG (Retrieval-Augmented Generation) Knowledge Assistant. Upload PDFs, DOCX, or CSVs and chat with them using AI.

This version uses **Streamlit** for the UI (instead of React) talking to the same FastAPI backend.

## Features

- Upload PDF, DOCX, CSV documents
- Automatic document chunking
- Embeddings via Ollama (local, free)
- Vector search with FAISS
- Full RAG pipeline with source citations
- Chat history per session
- JWT user authentication
- FastAPI backend + Streamlit frontend

## Architecture

```
User → Streamlit UI → FastAPI →
  ├── Upload → Parse → Chunk → Embed → FAISS Index
  └── Query  → Embed → Retrieve → LLM → Answer + Sources
```

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL
- [Ollama](https://ollama.ai) installed locally

### 1. Install Ollama Models
```bash
ollama pull llama3.2          # LLM for chat
ollama pull nomic-embed-text  # Embeddings
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy and configure env
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run DB migrations
alembic upgrade head

# Start server
uvicorn main:app --reload --port 8000
```

### 3. Streamlit Frontend Setup
```bash
cd streamlit_app
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

streamlit run app.py
```

App runs at: http://localhost:8501
API docs at: http://localhost:8000/docs

By default the Streamlit app points at `http://localhost:8000`. Override with:
```bash
export DOCUMIND_API_URL=http://your-backend-host:8000   # Windows: set DOCUMIND_API_URL=...
```

## Project Structure

```
documind/
├── backend/
│   ├── api/routes/          # FastAPI route handlers
│   │   ├── auth.py          # Login, register, JWT
│   │   ├── documents.py     # Upload, list, delete
│   │   └── chat.py          # Query, history
│   ├── core/
│   │   ├── config.py        # Settings from .env
│   │   └── security.py      # Password hash, JWT utils
│   ├── db/
│   │   └── database.py      # SQLAlchemy setup
│   ├── models/
│   │   └── models.py        # DB models: User, Document, Chunk, ChatMessage
│   ├── services/
│   │   ├── document_processor.py  # Parse PDF/DOCX/CSV, chunk
│   │   ├── embeddings.py          # Ollama embed via API
│   │   ├── vector_store.py        # FAISS index management
│   │   └── rag_pipeline.py        # Retrieve + generate answer
│   ├── main.py               # App entry point
│   └── requirements.txt
├── streamlit_app/
│   ├── app.py                 # Entry point — routes between login/dashboard
│   ├── auth_view.py           # Login / Register screen
│   ├── dashboard_view.py      # Sidebar (uploads/docs) + chat interface
│   ├── api_client.py          # requests-based API client (mirrors api.js)
│   └── requirements.txt
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Create account |
| POST | `/auth/login` | Get JWT token |
| POST | `/documents/upload` | Upload & process file |
| GET | `/documents/` | List user's documents |
| DELETE | `/documents/{id}` | Delete document |
| POST | `/chat/query` | Ask a question |
| GET | `/chat/history` | Get chat history |

## Streamlit vs React notes

- Auth state lives in `st.session_state` instead of `localStorage` + React `useState`. This means a hard refresh of the browser tab will log the user out (Streamlit reruns the script from scratch and `st.session_state` is tied to the browser session, not persisted to disk). If you need persistent login across refreshes, consider storing the token in a signed cookie via `streamlit-cookies-manager` or similar.
- Polling-after-upload (the `setTimeout` calls in the old `Dashboard.jsx`) is replaced with an explicit **Refresh** button, since Streamlit doesn't have a native background timer — you can re-add auto-refresh with `st_autorefresh` from `streamlit-extras` if you want it.
- The chat UI uses Streamlit's native `st.chat_message` / `st.chat_input` components instead of hand-rolled bubble divs.
- Source citations are shown in an `st.expander` per message instead of a click-to-toggle chip.

## Concepts You'll Learn

- **RAG Pipeline**: Retrieve relevant chunks → augment prompt → generate answer
- **Embeddings**: Convert text to vectors with Ollama's nomic-embed-text
- **Vector Search**: FAISS cosine similarity search
- **Chunking**: Splitting documents into overlapping chunks for better retrieval
- **JWT Auth**: Stateless authentication with access tokens
- **FastAPI**: Async Python API with auto-generated docs
- **Streamlit**: Building data/AI apps with pure Python, no JS required

## Docker (Optional)

```bash
docker-compose up --build
```
