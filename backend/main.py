from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from db.database import create_tables
from api.routes import auth, documents, chat

app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready RAG Knowledge Assistant — Ask your documents anything.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS — allow Streamlit dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.on_event("startup")
def startup():
    create_tables()
    print(f"🧠 {settings.APP_NAME} started")
    print(f"📄 Docs: http://localhost:8000/docs")


@app.get("/")
def root():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {"status": "ok"}
