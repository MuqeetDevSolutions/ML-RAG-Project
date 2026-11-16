"""
Repositories — high-level CRUD helpers.

Yeh functions SQLAlchemy session lete hain aur database operations
perform karte hain. Routers/services inhe call karte hain.

Fayda: business logic me raw SQLAlchemy queries nahi likhne padte.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from sqlalchemy import select, func, delete as sql_delete
from sqlalchemy.orm import Session

from app.db.models import Document, Conversation, Message


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ================================================================
# Documents
# ================================================================

def upsert_document(
    db: Session,
    document_id: str,
    file_name: str,
    file_path: Optional[str] = None,
    size_bytes: Optional[int] = None,
    total_pages: int = 0,
    chunk_count: int = 0,
) -> Document:
    """
    Document insert ya update karo.

    Agar document_id pehle se mojood hai to uske fields update ho jate hain.
    """
    doc = db.get(Document, document_id)
    if doc is None:
        doc = Document(
            document_id=document_id,
            file_name=file_name,
            file_path=file_path,
            size_bytes=size_bytes,
            total_pages=total_pages,
            chunk_count=chunk_count,
            uploaded_at=_utcnow(),
        )
        db.add(doc)
    else:
        doc.file_name = file_name
        doc.file_path = file_path
        doc.size_bytes = size_bytes
        doc.total_pages = total_pages
        doc.chunk_count = chunk_count

    db.flush()
    return doc


def get_document(db: Session, document_id: str) -> Optional[Document]:
    return db.get(Document, document_id)


def list_documents_db(db: Session) -> List[Document]:
    stmt = select(Document).order_by(Document.uploaded_at.desc())
    return list(db.execute(stmt).scalars().all())


def delete_document_db(db: Session, document_id: str) -> int:
    """Return: number of rows deleted (0 ya 1)."""
    doc = db.get(Document, document_id)
    if doc is None:
        return 0
    db.delete(doc)
    db.flush()
    return 1


def count_documents(db: Session) -> int:
    stmt = select(func.count(Document.document_id))
    return int(db.execute(stmt).scalar() or 0)


# ================================================================
# Conversations
# ================================================================

def create_conversation(db: Session, conversation_id: Optional[str] = None) -> Conversation:
    cid = conversation_id or str(uuid.uuid4())
    conv = Conversation(
        conversation_id=cid,
        created_at=_utcnow(),
        updated_at=_utcnow(),
    )
    db.add(conv)
    db.flush()
    return conv


def get_conversation(db: Session, conversation_id: str) -> Optional[Conversation]:
    return db.get(Conversation, conversation_id)


def get_or_create_conversation(
    db: Session, conversation_id: Optional[str]
) -> Conversation:
    if conversation_id:
        conv = get_conversation(db, conversation_id)
        if conv is not None:
            return conv
    return create_conversation(db, conversation_id)


def list_conversations(db: Session, limit: int = 100) -> List[Conversation]:
    stmt = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_conversation(db: Session, conversation_id: str) -> bool:
    conv = db.get(Conversation, conversation_id)
    if conv is None:
        return False
    db.delete(conv)
    db.flush()
    return True


def count_conversations(db: Session) -> int:
    stmt = select(func.count(Conversation.conversation_id))
    return int(db.execute(stmt).scalar() or 0)


def touch_conversation(db: Session, conversation_id: str) -> None:
    conv = db.get(Conversation, conversation_id)
    if conv is not None:
        conv.updated_at = _utcnow()
        db.flush()


# ================================================================
# Messages
# ================================================================

def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources: Optional[List[Dict[str, Any]]] = None,
) -> Message:
    sources_json = json.dumps(sources or []) if role == "assistant" else None
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        sources_json=sources_json,
        created_at=_utcnow(),
    )
    db.add(msg)
    db.flush()
    touch_conversation(db, conversation_id)
    return msg


def get_messages(
    db: Session, conversation_id: str, limit: Optional[int] = None
) -> List[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc(), Message.message_id.asc())
    )
    if limit:
        # Last N messages ke liye: ulta sort karke limit lagao, phir wapas
        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.message_id.desc())
            .limit(limit)
        )
        rows = list(db.execute(stmt).scalars().all())
        return list(reversed(rows))
    return list(db.execute(stmt).scalars().all())


def count_messages(db: Session, conversation_id: str) -> int:
    stmt = select(func.count(Message.message_id)).where(
        Message.conversation_id == conversation_id
    )
    return int(db.execute(stmt).scalar() or 0)


def delete_all_messages(db: Session, conversation_id: str) -> int:
    stmt = sql_delete(Message).where(Message.conversation_id == conversation_id)
    result = db.execute(stmt)
    db.flush()
    return int(result.rowcount or 0)