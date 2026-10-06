"""
Application configuration.

Yeh module .env file se saari settings load karta hai.
Har jagah directly os.getenv() call karne ke bajaye,
ek jagah "settings" object banate hain — code saaf aur
maintainable rehta hai.
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Project root = is file ka parent.parent.parent
# (app/core/config.py -> app/core -> app -> project root)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# .env file project root me hai
load_dotenv(PROJECT_ROOT / ".env")


class Settings:
    """Simple settings container. Values .env ya defaults se aati hain."""

    # --- App ---
    APP_NAME: str = os.getenv("APP_NAME", "RAG Document QA")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # --- OpenAI ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # --- Paths (project root ke relative) ---
    PROJECT_ROOT: Path = PROJECT_ROOT
    UPLOAD_DIR: Path = PROJECT_ROOT / os.getenv("UPLOAD_DIR", "data/uploads")
    VECTORSTORE_DIR: Path = PROJECT_ROOT / os.getenv("VECTORSTORE_DIR", "data/vectorstore")

    # --- Database ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'data' / 'app.db'}")

    # --- RAG settings ---
    EMBEDDING_MODEL: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "800"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))
    TOP_K: int = int(os.getenv("TOP_K", "5"))

    def ensure_dirs(self) -> None:
        """Zaroori folders mojood na hon to bana do."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)


# Ek hi instance poore app me use hoga
settings = Settings()
settings.ensure_dirs()