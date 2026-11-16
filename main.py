"""
RAG Document QA — application entry point.

Production features:
    - Structured logging (console + rotating file)
    - Global error handlers
    - Request logging middleware
    - Security headers
    - /api/status endpoint
"""

import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging_config import configure_logging, get_logger
from app.core.errors import register_error_handlers
from app.core.status import get_full_status
from app.db.session import init_db
from app.api import documents, ask, chat


# Logging setup — sab se pehle
configure_logging()
logger = get_logger("app.main")


FRONTEND_DIR = settings.PROJECT_ROOT / "frontend"


app = FastAPI(
    title=settings.APP_NAME,
    description="RAG Document QA — PDF upload karo aur uske bare me sawaal poocho",
    version="0.8.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------
# Request logging middleware
# ----------------------------------------------------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.time()
    try:
        response = await call_next(request)
    except Exception:
        # Error handlers ne log kiya, yahan sirf timing
        elapsed = (time.time() - t0) * 1000
        logger.exception(
            "%s %s | UNHANDLED | %.1fms",
            request.method, request.url.path, elapsed,
        )
        raise

    elapsed = (time.time() - t0) * 1000

    # Skip health checks ka log (spam)
    if request.url.path not in ("/health", "/api/status"):
        logger.info(
            "%s %s | %d | %.1fms",
            request.method, request.url.path,
            response.status_code, elapsed,
        )

    return response


# ----------------------------------------------------------------
# Security headers middleware
# ----------------------------------------------------------------

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )
    return response


# ----------------------------------------------------------------
# Routers
# ----------------------------------------------------------------

app.include_router(documents.router)
app.include_router(ask.router)
app.include_router(chat.router)


# ----------------------------------------------------------------
# Error handlers
# ----------------------------------------------------------------

register_error_handlers(app)


# ----------------------------------------------------------------
# Startup
# ----------------------------------------------------------------

@app.on_event("startup")
def on_startup() -> None:
    logger.info("=" * 60)
    logger.info("Starting %s v0.8.0", settings.APP_NAME)
    logger.info("Environment: %s", settings.APP_ENV)

    # DB init
    init_db()
    logger.info("Database ready")

    # Status check
    status = get_full_status()
    logger.info("System status: %s", status["status"])
    for name, check in status["checks"].items():
        ok = "OK" if check.get("ok") else "FAIL"
        logger.info("  [%s] %s", ok, name)

    # Warning agar LLM key nahi hai
    if not status["checks"]["llm"]["ok"]:
        logger.warning(
            "GROQ_API_KEY set nahi hai — LLM features kaam nahi karenge. "
            "'.env' file check karo."
        )

    logger.info("=" * 60)


@app.on_event("shutdown")
def on_shutdown() -> None:
    logger.info("Shutting down...")


# ----------------------------------------------------------------
# Frontend
# ----------------------------------------------------------------

if FRONTEND_DIR.exists():
    app.mount(
        "/static",
        StaticFiles(directory=str(FRONTEND_DIR)),
        name="static",
    )


@app.get("/", include_in_schema=False)
def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"error": "frontend/index.html mojood nahi"}
    return FileResponse(str(index_path))


# ----------------------------------------------------------------
# Meta endpoints
# ----------------------------------------------------------------

@app.get("/health", tags=["meta"])
def health():
    """Lightweight health check — sirf "server zinda hai"."""
    return {"status": "ok", "version": "0.8.0"}


@app.get("/api/status", tags=["meta"])
def full_status():
    """Detailed system status — DB, store, LLM, disk."""
    return get_full_status()


@app.get("/api/info", tags=["meta"])
def api_info():
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "environment": settings.APP_ENV,
        "version": "0.8.0",
        "docs": "/docs",
    }