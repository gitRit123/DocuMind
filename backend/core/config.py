from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/documind"

    # JWT
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3.2"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Storage
    UPLOAD_DIR: str = "./uploads"
    FAISS_INDEX_DIR: str = "./faiss_indexes"

    # RAG settings
    CHUNK_SIZE: int = 500          # chars per chunk
    CHUNK_OVERLAP: int = 50        # overlap between chunks
    TOP_K_RESULTS: int = 5         # chunks to retrieve per query

    # App
    APP_NAME: str = "DocuMind"
    DEBUG: bool = True

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure directories exist
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(settings.FAISS_INDEX_DIR).mkdir(parents=True, exist_ok=True)
