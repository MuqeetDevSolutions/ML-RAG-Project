"""
Ask API — RAG pipeline ko HTTP ke through expose karo.

Endpoint:
    POST /api/ask

Flow:
    1. Client JSON body bhejta hai: {"question": "...", "top_k": 8}
    2. Hum RAGPipeline se answer lete hain
    3. Answer + sources JSON me convert karke return karte hain

RAGPipeline ka instance singleton hai (store_manager jaisa) taake
har request par model load na ho.
"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    AskRequest,
    AskResponse,
    SourceSchema,
    SourceChunk,
)
from app.services.rag_pipeline import RAGPipeline
from app.services.store_manager import get_store


router = APIRouter(prefix="/api", tags=["ask"])


# ----------------------------------------------------------------
# Pipeline singleton
# ----------------------------------------------------------------

_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    """
    Ek hi RAGPipeline instance return karo (singleton).

    Pipeline store ko internally rakhta hai — hum usko
    store_manager ke singleton se pass karte hain taake
    upload/delete ke baad same store use ho.
    """
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline(store=get_store())
    return _pipeline


# ----------------------------------------------------------------
# Endpoint
# ----------------------------------------------------------------

@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    """
    Sawaal poocho, answer + sources paao.

    Agar store khaali hai ya sawaal ka jawab documents me nahi hai,
    `found_in_documents: false` aur saaf message milta hai.
    """
    t0 = time.time()

    # Validation
    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question khaali nahi ho sakta.",
        )

    # Store empty check
    store = get_store()
    if store.is_empty:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Koi document upload nahi hua. Pehle PDF upload karo.",
        )

    # RAG pipeline
    pipeline = get_pipeline()

    try:
        # min_score override (agar request me diya ho)
        kwargs = {"top_k": request.top_k}
        if request.min_score is not None:
            kwargs["min_score"] = request.min_score

        ra = pipeline.ask(question, **kwargs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {type(e).__name__}: {e}",
        )

    # Sources ko schema me convert
    sources_schema = []
    for g in ra.used_sources:
        chunks = [
            SourceChunk(
                chunk_id=c["chunk_id"],
                score=c["score"],
                preview=c["preview"],
                char_count=c.get("char_count", 0),
            )
            for c in g.get("chunks", [])
        ]
        sources_schema.append(
            SourceSchema(
                file_name=g["file_name"],
                page_number=g["page_number"],
                best_score=g["best_score"],
                chunk_count=g.get("chunk_count", len(chunks)),
                chunks=chunks,
            )
        )

    elapsed = round(time.time() - t0, 2)

    return AskResponse(
        question=ra.question,
        answer=ra.answer,
        found_in_documents=ra.found_in_documents,
        top_score=round(ra.top_score, 4),
        sources=sources_schema,
        retrieved_count=len(ra.retrieved_chunks),
        elapsed_seconds=elapsed,
    )