"""
SQLAlchemy models — database tables.

Tables:
    documents       — uploaded PDFs ka metadata
    conversations   — chat sessions
    messages        — individual turns (user + assistant) in a chat

Yeh SQLAlchemy 2.0 style hai (Mapped, mapped_column) — modern Pythonic.
"""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all models."""
    pass


# ================================================================
# Documents
# ================================================================

class Document(Base):
    """
    Ek uploaded PDF ka metadata.

    Actual chunks + embeddings FAISS me hote hain; yahan sirf
    metadata (search/filter/listing ke liye).
    """
    __tablename__ = "documents"

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), index=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    # Optional: user/collection feature aage ke liye
    collection: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)

    def __repr__(self) -> str:
        return f"<Document {self.document_id[:8]} {self.file_name}>"


# ================================================================
# Conversations + Messages
# ================================================================

class Conversation(Base):
    """Ek chat session."""
    __tablename__ = "conversations"

    conversation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    messages: Mapped[List["Message"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.conversation_id[:8]}>"


class Message(Base):
    """Ek single message (user ya assistant)."""
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.conversation_id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[str] = mapped_column(String(16))    # "user" ya "assistant"
    content: Mapped[str] = mapped_column(Text)

    # Sources JSON string (assistant messages ke liye; user messages me null)
    sources_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.message_id} {self.role}>"