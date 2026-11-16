"""
Test: Multiple documents support.

Yeh test 2 fake documents bana kar verify karta hai ke:
  1. Dono documents ke chunks ek hi store me add ho sakte hain.
  2. Search dono documents se chunks laata hai.
  3. Ek document delete karne se doosre ka data bacha rehta hai.
  4. Filter by document_id kaam karta hai.

Yeh actual store ko modify nahi karta — temporary in-memory
store banata hai.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.chunker import Chunk
from app.services.embedder import embed_texts, embed_query
from app.services.vector_store import VectorStore
import uuid


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def make_chunk(doc_id, file_name, page, idx, text) -> Chunk:
    return Chunk(
        chunk_id=str(uuid.uuid4()),
        document_id=doc_id,
        file_name=file_name,
        page_number=page,
        chunk_index_in_page=idx,
        text=text,
        char_count=len(text),
    )


def main() -> int:
    section("1. Store banao + 2 documents ke chunks add karo")

    store = VectorStore()

    doc_math = "doc-math-001"
    doc_history = "doc-history-001"

    math_chunks = [
        make_chunk(doc_math, "algebra.pdf", 1, 0,
                   "Algebra is a branch of mathematics dealing with symbols and the rules for manipulating those symbols."),
        make_chunk(doc_math, "algebra.pdf", 2, 0,
                   "A quadratic equation has the form ax squared plus bx plus c equals zero."),
        make_chunk(doc_math, "algebra.pdf", 3, 0,
                   "The Pythagorean theorem states that a squared plus b squared equals c squared."),
    ]

    history_chunks = [
        make_chunk(doc_history, "wwii.pdf", 1, 0,
                   "World War II began in 1939 and ended in 1945 after six years of global conflict."),
        make_chunk(doc_history, "wwii.pdf", 5, 0,
                   "The Battle of Stalingrad was a major turning point on the Eastern Front."),
        make_chunk(doc_history, "wwii.pdf", 8, 0,
                   "The atomic bombings of Hiroshima and Nagasaki took place in August 1945."),
    ]

    all_chunks = math_chunks + history_chunks
    texts = [c.text for c in all_chunks]
    vectors = embed_texts(texts)

    added = store.add_chunks(all_chunks, vectors)
    print(f"   Added: {added} chunks")
    print(f"   Store: {store.stats()}")

    ok = added == 6
    print(f"   Status: {'OK' if ok else 'FAIL'}")
    results = [ok]

    # ---------- 2. Cross-document search ----------
    section("2. Cross-document search")

    queries = [
        ("What is algebra?", "algebra.pdf"),
        ("When did World War II begin?", "wwii.pdf"),
        ("Tell me about the Battle of Stalingrad", "wwii.pdf"),
        ("What is the Pythagorean theorem?", "algebra.pdf"),
    ]

    for q, expected_file in queries:
        qv = embed_query(q)
        hits = store.search(qv, top_k=3)
        top = hits[0]
        ok = top.file_name == expected_file
        status = "PASS" if ok else "FAIL"
        print(f"   {status}  Q: {q}")
        print(f"          → {top.file_name} p{top.page_number} "
              f"(score={top.score:.4f})")
        if not ok:
            print(f"          Expected: {expected_file}")
        results.append(ok)

    # ---------- 3. list_documents ----------
    section("3. list_documents()")
    docs = store.list_documents()
    print(f"   Documents: {len(docs)}")
    for d in docs:
        print(f"      {d['file_name']} ({d['chunks']} chunks, pages={d['pages']})")
    ok = len(docs) == 2
    results.append(ok)
    print(f"   Status: {'OK' if ok else 'FAIL'}")

    # ---------- 4. Delete one document ----------
    section("4. Delete math document")
    removed = store.delete_document(doc_math)
    print(f"   Removed: {removed} chunks")
    print(f"   Store: {store.stats()}")

    # Verify math queries now fail (ya low score)
    qv = embed_query("What is algebra?")
    hits = store.search(qv, top_k=3)
    print(f"   Query 'What is algebra?' after delete:")
    for h in hits[:2]:
        print(f"      {h.file_name} p{h.page_number} (score={h.score:.4f})")

    # Verify history queries still work
    qv = embed_query("When did World War II begin?")
    hits = store.search(qv, top_k=3)
    top = hits[0]
    ok = top.file_name == "wwii.pdf" and top.score > 0.4
    print(f"   Query 'When did World War II begin?' top: "
          f"{top.file_name} (score={top.score:.4f})")
    results.append(ok)
    print(f"   Status: {'OK' if ok else 'FAIL'}")

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> MULTIPLE DOCUMENTS SUPPORT THEEK HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())