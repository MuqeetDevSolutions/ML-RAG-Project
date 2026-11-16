"""
System status check — health endpoint ke liye.

Checks:
    - SQLite DB reachable
    - Vector store mojood + non-empty
    - Groq API key set
    - Uploads folder writable
    - Disk space (basic)
"""

import shutil
from pathlib import Path
from typing import Dict, Any

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.services.store_manager import get_store


def check_database() -> Dict[str, Any]:
    """DB reachable? Table mojood hain?"""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            # Count tables
            res = db.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in res.fetchall()]
        return {
            "ok": True,
            "tables": tables,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def check_vector_store() -> Dict[str, Any]:
    """Vector store load hua? Non-empty?"""
    try:
        store = get_store()
        stats = store.stats()
        return {
            "ok": True,
            "vectors": stats["total_vectors"],
            "documents": stats["unique_documents"],
            "dimension": stats["dimension"],
            "is_empty": store.is_empty,
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def check_llm_config() -> Dict[str, Any]:
    """LLM API key set hai?"""
    key = settings.GROQ_API_KEY or ""
    is_set = bool(key) and not key.startswith("gsk-your")
    return {
        "ok": is_set,
        "provider": "groq",
        "model": settings.LLM_MODEL,
        "key_set": is_set,
    }


def check_disk() -> Dict[str, Any]:
    """Disk space + uploads folder writable?"""
    try:
        uploads = Path(settings.UPLOAD_DIR)
        uploads.mkdir(parents=True, exist_ok=True)
        test_file = uploads / ".write_test"
        test_file.write_text("test", encoding="utf-8")
        test_file.unlink()

        usage = shutil.disk_usage(str(settings.PROJECT_ROOT))
        free_mb = usage.free / (1024 * 1024)
        total_mb = usage.total / (1024 * 1024)
        return {
            "ok": True,
            "writable": True,
            "free_mb": round(free_mb, 1),
            "total_mb": round(total_mb, 1),
            "used_percent": round((usage.used / usage.total) * 100, 1),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def check_config() -> Dict[str, Any]:
    """Settings summary (keys masked)."""
    key = settings.GROQ_API_KEY or ""
    masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "(not set)"
    return {
        "ok": True,
        "app_env": settings.APP_ENV,
        "log_level": settings.LOG_LEVEL,
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "rerank_enabled": settings.RERANK_ENABLED,
        "query_rewrite_enabled": settings.QUERY_REWRITE_ENABLED,
        "chunk_size": settings.CHUNK_SIZE,
        "top_k": settings.TOP_K,
        "groq_key": masked,
    }


def get_full_status() -> Dict[str, Any]:
    """Sab checks ek saath."""
    db = check_database()
    vs = check_vector_store()
    llm = check_llm_config()
    disk = check_disk()
    cfg = check_config()

    # Overall health — critical cheezein theek hain?
    critical_ok = db["ok"] and vs["ok"] and llm["ok"] and disk["ok"]

    return {
        "status": "healthy" if critical_ok else "degraded",
        "checks": {
            "database": db,
            "vector_store": vs,
            "llm": llm,
            "disk": disk,
            "config": cfg,
        },
    }