"""
Chat API — stateful conversation with the RAG pipeline.

Endpoints:
    POST   /api/chat                    — sawaal poocho (memory ke sath)
    GET    /api/conversations           — saari conversations list
    GET    /api/conversations/{id}      — ek conversation ki poori history
    DELETE /api/conversations/{id}      — conversation delete karo

Note:
    ConversationStore ab SQLite-backed hai (Step 25). Methods:
        conv_store.get_or_create(id) → dict (not object)
        conv_store.history_dicts(id) → list of {role, content}
        conv_store.add_user_message(id, content)
        conv_store.add_assistant_message(id, content, sources)
"""

import time
from typing import Optional

from fastapi import APIRouter, HTTPException, status

from app.schemas import (
    ChatRequest,
    ChatResponse,
    SourceSchema,
    SourceChunk,
    ConversationInfo,
    ListConversationsResponse,
    ConversationDetailResponse,
    DeleteConversationResponse,
)
from app.services.rag_pipeline import RAGPipeline
from app.services.store_manager import get_store
from app.services.conversation_store import get_conversation_store


router = APIRouter(prefix="/api", tags=["chat"])


# ----------------------------------------------------------------
# Pipeline singleton
# ----------------------------------------------------------------

_pipeline: Optional[RAGPipeline] = None


def get_pipeline() -> RAGPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = RAGPipeline(store=get_store())
    return _pipeline


# ----------------------------------------------------------------
# Chat
# ----------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Sawaal poocho — conversation memory ke sath.

    Agar conversation_id diya, wahi continue hoga. Warna naya banega
    aur response me naya ID milega.
    """
    t0 = time.time()

    question = request.question.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question khaali nahi ho sakta.",
        )

    store = get_store()
    if store.is_empty:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Koi document upload nahi hua. Pehle PDF upload karo.",
        )

    # ---- Conversation get or create ----
    conv_store = get_conversation_store()
    conv = conv_store.get_or_create(request.conversation_id)
    cid = conv["conversation_id"]

    # ---- Previous history for LLM ----
    history = conv_store.history_dicts(cid)

    # ---- RAG pipeline ----
    pipeline = get_pipeline()
    try:
        kwargs = {"top_k": request.top_k, "history": history}
        if request.min_score is not None:
            kwargs["min_score"] = request.min_score
        ra = pipeline.ask(question, **kwargs)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG pipeline error: {type(e).__name__}: {e}",
        )

    # ---- Save this turn to DB ----
    conv_store.add_user_message(cid, question)
    conv_store.add_assistant_message(cid, ra.answer, sources=ra.used_sources)

    # ---- Sources schema ----
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

    # ---- Turn count (fresh from DB) ----
    detail = conv_store.get_full_conversation(cid)
    turn_count = detail["turn_count"] if detail else 0

    elapsed = round(time.time() - t0, 2)

    return ChatResponse(
        conversation_id=cid,
        question=ra.question,
        answer=ra.answer,
        found_in_documents=ra.found_in_documents,
        top_score=round(ra.top_score, 4),
        sources=sources_schema,
        retrieved_count=len(ra.retrieved_chunks),
        elapsed_seconds=elapsed,
        retrieval_query=ra.retrieval_query,
        turn_count=turn_count,
    )


# ----------------------------------------------------------------
# Conversations management
# ----------------------------------------------------------------

@router.get("/conversations", response_model=ListConversationsResponse)
def list_conversations():
    """Saari active conversations dikhao."""
    store = get_conversation_store()
    items = store.list_all()
    return ListConversationsResponse(
        total=len(items),
        conversations=[
            ConversationInfo(
                conversation_id=c["conversation_id"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                turn_count=c["turn_count"],
            )
            for c in items
        ],
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation(conversation_id: str):
    """Ek conversation ki poori history."""
    store = get_conversation_store()
    detail = store.get_full_conversation(conversation_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' nahi mili.",
        )
    return ConversationDetailResponse(**detail)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=DeleteConversationResponse,
)
def delete_conversation(conversation_id: str):
    """Conversation delete karo."""
    store = get_conversation_store()
    removed = store.delete(conversation_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' nahi mili.",
        )
    return DeleteConversationResponse(
        status="deleted",
        message="Conversation delete ho gayi.",
        conversation_id=conversation_id,
    )