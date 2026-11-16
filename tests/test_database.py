"""
Test: SQLite database persistence.

Verify karta hai:
  1. init_db() tables create karta hai
  2. Document row insert / retrieve
  3. Conversation row create / messages add
  4. History retrieval (LLM format)
  5. Delete cascade (conversation + messages)
  6. Persistence — file mojood hai disk par
"""

import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.db.session import SessionLocal, init_db, engine
from app.db import repositories as repo
from app.services.conversation_store import ConversationStore


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def main() -> int:
    results = []

    # ---------- 1. init_db ----------
    section("1. init_db() — tables create")
    init_db()
    db_path = settings.PROJECT_ROOT / "data" / "app.db"
    print(f"   DB path: {db_path}")
    print(f"   Exists:  {db_path.exists()}")
    if db_path.exists():
        print(f"   Size:    {db_path.stat().st_size} bytes")
    ok = db_path.exists()
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 2. Document insert ----------
    section("2. Document insert / retrieve")
    test_doc_id = f"test-{uuid.uuid4().hex[:8]}"
    with SessionLocal() as db:
        doc = repo.upsert_document(
            db,
            document_id=test_doc_id,
            file_name="test_doc.pdf",
            file_path="/tmp/test_doc.pdf",
            size_bytes=12345,
            total_pages=10,
            chunk_count=42,
        )
        db.commit()

    with SessionLocal() as db:
        fetched = repo.get_document(db, test_doc_id)
        print(f"   Inserted:  {test_doc_id}")
        print(f"   Retrieved: {fetched.file_name}, {fetched.chunk_count} chunks, "
              f"{fetched.total_pages} pages")
        ok = fetched is not None and fetched.chunk_count == 42
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")

        # Cleanup
        repo.delete_document_db(db, test_doc_id)
        db.commit()

    # ---------- 3. Conversation create + messages ----------
    section("3. Conversation + messages")
    store = ConversationStore()
    conv = store.create()
    cid = conv["conversation_id"]
    print(f"   Conversation: {cid[:8]}...")

    store.add_user_message(cid, "Who is Carl?")
    store.add_assistant_message(
        cid, "Carl is a watchmaker.",
        sources=[{"file_name": "sample.pdf", "page_number": 81, "best_score": 0.52}],
    )

    detail = store.get_full_conversation(cid)
    print(f"   Turn count: {detail['turn_count']} (expect 2)")
    for t in detail["turns"]:
        print(f"      [{t['role']}] {t['content'][:60]}...")

    ok = detail["turn_count"] == 2
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 4. History for LLM ----------
    section("4. History (LLM format)")
    history = store.history_dicts(cid)
    print(f"   History turns: {len(history)}")
    for h in history:
        print(f"      {h['role']}: {h['content'][:50]}...")
    ok = len(history) == 2 and history[0]["role"] == "user"
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 5. List conversations ----------
    section("5. List conversations")
    items = store.list_all()
    print(f"   Total: {len(items)}")
    found = any(c["conversation_id"] == cid for c in items)
    print(f"   Our conv found: {found}")
    ok = found
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 6. Delete cascade ----------
    section("6. Delete conversation (cascade)")
    before_count = store.count()
    ok_del = store.delete(cid)
    after_count = store.count()
    print(f"   Deleted: {ok_del}")
    print(f"   Before count: {before_count}, after: {after_count}")

    # Verify messages gone too (SQLite cascade)
    with SessionLocal() as db:
        msgs = repo.get_messages(db, cid)
        print(f"   Messages after delete: {len(msgs)} (expect 0)")
    ok = ok_del and after_count == before_count - 1 and len(msgs) == 0
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 7. Persistence across sessions ----------
    section("7. Persistence across sessions")
    conv2 = store.create()
    cid2 = conv2["conversation_id"]
    store.add_user_message(cid2, "Test persistence")

    # New "session" — same store instance but new DB connection
    store2 = ConversationStore()
    detail2 = store2.get_full_conversation(cid2)
    print(f"   Conversation from 'new' store: {detail2 is not None}")
    print(f"   Turn count: {detail2['turn_count'] if detail2 else 'N/A'}")
    ok = detail2 is not None and detail2["turn_count"] == 1
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # Cleanup
    store2.delete(cid2)

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> DATABASE THEEK KAAM KAR RAHI HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())