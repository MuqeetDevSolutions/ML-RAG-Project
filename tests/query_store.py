"""
Query script: vector store se sawaal poocho (interactive).

Yeh script:
  1. Disk se vector store load karta hai.
  2. Loop me aap se sawaal leta hai.
  3. Har sawaal ka embedding bana kar top-K chunks dikhata hai.

Chalane ka tareeqa:
    python tests\\query_store.py

Exit karne ke liye: 'quit', 'exit', ya 'q' likho.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.embedder import embed_query
from app.services.vector_store import VectorStore


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def print_results(query: str, results) -> None:
    print()
    print(f"  Query: {query}")
    print(f"  Results: {len(results)}")
    print("  " + "-" * 56)

    for i, r in enumerate(results, 1):
        text = r.text.replace("\n", " ").strip()
        preview = text[:280] + ("..." if len(text) > 280 else "")
        print(f"\n  #{i}  score={r.score:+.4f}")
        print(f"      file:  {r.file_name}")
        print(f"      page:  {r.page_number}")
        print(f"      chunk: {r.chunk_id[:8]}...")
        print(f"      text:  {preview}")


def main() -> int:
    section("Vector Store Query (Interactive)")

    store = VectorStore.load()
    if store.is_empty:
        print("  Store khaali hai. Pehle chalao:")
        print("      python tests\\ingest_pdfs.py")
        return 1

    stats = store.stats()
    print(f"  Total vectors:    {stats['total_vectors']}")
    print(f"  Unique documents: {stats['unique_documents']}")
    print(f"  Files:            {stats['unique_files']}")
    print()
    print("  Type a question. Type 'quit' to exit.")
    print()

    while True:
        try:
            q = input("Q> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            break

        vec = embed_query(q)
        hits = store.search(vec, top_k=5)

        if not hits:
            print("   (koi result nahi mila)")
            continue

        print_results(q, hits)

    print()
    print("Bye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())