"""
Pydantic schemas — API ke request/response models.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


# ================================================================
# Documents
# ================================================================

class DocumentInfo(BaseModel):
    document_id: str
    file_name: str
    chunks: int
    pages: List[int]


class UploadResponse(BaseModel):
    status: str
    message: str
    document_id: Optional[str] = None
    file_name: Optional[str] = None
    total_pages: Optional[int] = None
    chunks_added: Optional[int] = None
    warnings: List[str] = Field(default_factory=list)
    elapsed_seconds: Optional[float] = None


class ListDocumentsResponse(BaseModel):
    total_documents: int
    total_chunks: int
    documents: List[DocumentInfo]


class DeleteResponse(BaseModel):
    status: str
    message: str
    document_id: str
    chunks_removed: int = 0


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.5.0"


# ================================================================
# Ask (stateless)
# ================================================================

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=20)
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class SourceChunk(BaseModel):
    chunk_id: str
    score: float
    preview: str
    char_count: int


class SourceSchema(BaseModel):
    file_name: str
    page_number: int
    best_score: float
    chunk_count: int
    chunks: List[SourceChunk]


class AskResponse(BaseModel):
    question: str
    answer: str
    found_in_documents: bool
    top_score: float
    sources: List[SourceSchema] = Field(default_factory=list)
    retrieved_count: int = 0
    elapsed_seconds: float = 0.0
    retrieval_query: str = ""


# ================================================================
# Chat (stateful)
# ================================================================

class ChatRequest(BaseModel):
    """Chat endpoint ka request body."""
    conversation_id: Optional[str] = Field(
        default=None,
        description="Pichle chat ka ID (agar continue karna hai). Naya chat ke liye null.",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="User ka sawaal",
    )
    top_k: int = Field(default=8, ge=1, le=20)
    min_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ChatResponse(BaseModel):
    """Chat endpoint ka response."""
    conversation_id: str
    question: str
    answer: str
    found_in_documents: bool
    top_score: float
    sources: List[SourceSchema] = Field(default_factory=list)
    retrieved_count: int = 0
    elapsed_seconds: float = 0.0
    retrieval_query: str = ""
    turn_count: int = 0


class ConversationInfo(BaseModel):
    """Conversation ki summary (list ke liye)."""
    conversation_id: str
    created_at: str
    updated_at: str
    turn_count: int


class ListConversationsResponse(BaseModel):
    total: int
    conversations: List[ConversationInfo]


class ConversationDetailResponse(BaseModel):
    """Poori conversation (turns ke sath)."""
    conversation_id: str
    created_at: str
    updated_at: str
    turn_count: int
    turns: List[Dict[str, Any]]


class DeleteConversationResponse(BaseModel):
    status: str
    message: str
    conversation_id: str