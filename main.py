"""
RAG Document QA — application entry point.

Abhi yeh sirf ek hello-world route aur ek health-check
route de raha hai. Aage ke steps me hum yahan aur bhi
routes add karenge.
"""

from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="PDF documents par sawaal-jawab karne wala RAG system",
    version="0.1.0",
)


@app.get("/")
def root():
    """Root endpoint — server zinda hai ya nahi dekhne ke liye."""
    return {
        "app": settings.APP_NAME,
        "status": "running",
        "environment": settings.APP_ENV,
    }


@app.get("/health")
def health():
    """Simple health check."""
    return {"status": "ok"}