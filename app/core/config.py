"""
Application configuration.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Simple settings container."""

    # --- App ---
    APP_NAME: str = os.getenv("APP_NAME", "RAG Document QA")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- LLM (Groq) ---
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "800"))

    # --- Paths ---
    PROJECT_ROOT: Path = PROJECT_ROOT
    UPLOAD_DIR: Path = PROJECT_ROOT / os.getenv("UPLOAD_DIR", "data/uploads")
    VECTORSTORE_DIR: Path = PROJECT_ROOT / os.getenv("VECTORSTORE_DIR", "data/vectorstore")

    # --- Database ---
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}"
    )

    # --- RAG settings ---
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    TOP_K: int = int(os.getenv("TOP_K", "8"))

    # --- Reranking ---
    RERANK_MODEL: str = os.getenv(
        "RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
    )
    RERANK_ENABLED: bool = os.getenv("RERANK_ENABLED", "true").lower() in ("1", "true", "yes")
    RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "20"))
    RERANK_TOP_N: int = int(os.getenv("RERANK_TOP_N", "8"))

    # --- Query Rewriting (Phase 15) ---
    # Agar on hai, follow-up questions LLM se standalone banaye jate hain
    QUERY_REWRITE_ENABLED: bool = os.getenv(
        "QUERY_REWRITE_ENABLED", "true"
    ).lower() in ("1", "true", "yes")
    # Rewrite ke liye kitne history turns use karne hain
    QUERY_REWRITE_MAX_HISTORY: int = int(os.getenv("QUERY_REWRITE_MAX_HISTORY", "6"))

    def ensure_dirs(self) -> None:
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()