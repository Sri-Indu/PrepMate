"""Load settings from environment variables (and an optional .env file).

Pydantic Settings maps env names like FRONTEND_ORIGIN to fields like
frontend_origin. No secrets are hardcoded.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/core/config.py -> PrepMate/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:3000"

    llm_provider: str = "ollama"
    llm_base_url: str = "http://127.0.0.1:11434"
    llm_model: str = "gemma2:2b"
    llm_api_key: str = ""
    llm_timeout_seconds: float = 120.0

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    database_path: str = "./backend/data/prepmate.db"

    # Resumes/JDs are processed in memory only. 5 MiB is enough for typical PDFs.
    max_upload_bytes: int = 5 * 1024 * 1024

    # RAG: overlapping character windows. Smaller chunks = more precise retrieval.
    rag_chunk_size: int = 400
    rag_chunk_overlap: int = 80
    rag_top_k: int = 4


settings = Settings()
