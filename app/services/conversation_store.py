"""
Conversation store — SQLite-backed.

Pehle in-memory dictionary thi. Ab SQLite use karti hai (SQLAlchemy).
Server restart ke baad bhi conversations persist rehti hain.

Design:
- Har method ek SQLAlchemy session leta hai
- Session caller (route) provide karta hai — `with SessionLocal() as db`
- Trim policy: agar history bohot lambi ho, sirf last N messages LLM ko
  bhejenge (DB me sab rehta hai, bas prompt chhota rakhte hain)
"""

from typing import Optional, List, Dict, Any

from app.db.session import SessionLocal
from app.db import repositories as repo


# Kitne recent messages LLM ko bhejein (chat history ke liye)
DEFAULT_HISTORY_MESSAGES = 12   # ~6 exchanges


class ConversationStore:
    """
    Thin wrapper — actually SQLite me store hota hai.

    Har method apna session open karta hai taake standalone use ho sake.
    FastAPI route me hum `with SessionLocal() as db: ...` use karenge.
    """

    # ---------- Create / Get ----------

    def create(self) -> Dict[str, Any]:
        with SessionLocal() as db:
            conv = repo.create_conversation(db)
            db.commit()
            return {
                "conversation_id": conv.conversation_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "turn_count": 0,
            }

    def get_or_create(self, conversation_id: Optional[str]) -> Dict[str, Any]:
        with SessionLocal() as db:
            conv = repo.get_or_create_conversation(db, conversation_id)
            db.commit()
            count = repo.count_messages(db, conv.conversation_id)
            return {
                "conversation_id": conv.conversation_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "turn_count": count,
            }

    def get(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with SessionLocal() as db:
            conv = repo.get_conversation(db, conversation_id)
            if conv is None:
                return None
            count = repo.count_messages(db, conv.conversation_id)
            return {
                "conversation_id": conv.conversation_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "turn_count": count,
            }

    def delete(self, conversation_id: str) -> bool:
        with SessionLocal() as db:
            ok = repo.delete_conversation(db, conversation_id)
            db.commit()
            return ok

    def list_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        with SessionLocal() as db:
            convs = repo.list_conversations(db, limit=limit)
            out = []
            for c in convs:
                count = repo.count_messages(db, c.conversation_id)
                out.append({
                    "conversation_id": c.conversation_id,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                    "turn_count": count,
                })
            return out

    def count(self) -> int:
        with SessionLocal() as db:
            return repo.count_conversations(db)

    # ---------- Messages ----------

    def add_user_message(self, conversation_id: str, content: str) -> Dict[str, Any]:
        with SessionLocal() as db:
            msg = repo.add_message(db, conversation_id, "user", content)
            db.commit()
            return {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
            }

    def add_assistant_message(
        self,
        conversation_id: str,
        content: str,
        sources: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        with SessionLocal() as db:
            msg = repo.add_message(db, conversation_id, "assistant", content, sources)
            db.commit()
            return {
                "message_id": msg.message_id,
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.created_at.isoformat(),
                "source_count": len(sources or []),
            }

    def history_dicts(
        self,
        conversation_id: str,
        limit: int = DEFAULT_HISTORY_MESSAGES,
    ) -> List[Dict[str, str]]:
        """
        LLM ke liye recent history — list of {"role", "content"}.
        """
        with SessionLocal() as db:
            messages = repo.get_messages(db, conversation_id, limit=limit)
            return [
                {"role": m.role, "content": m.content}
                for m in messages
                if m.role in ("user", "assistant") and m.content
            ]

    def get_full_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Poori conversation — turns ke sath (UI ke liye)."""
        with SessionLocal() as db:
            conv = repo.get_conversation(db, conversation_id)
            if conv is None:
                return None
            messages = repo.get_messages(db, conversation_id)
            return {
                "conversation_id": conv.conversation_id,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat(),
                "turn_count": len(messages),
                "turns": [
                    {
                        "role": m.role,
                        "content": m.content,
                        "timestamp": m.created_at.isoformat(),
                    }
                    for m in messages
                ],
            }


# ----------------------------------------------------------------
# Singleton (thin — actual data DB me hai)
# ----------------------------------------------------------------

_store: Optional[ConversationStore] = None


def get_conversation_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store