"""
Chota script: store me mojood documents ki list dikhao.

    python tests\\list_documents.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.vector_store import VectorStore


def main() -> int:
    store = VectorStore.load()

    print()
    print("=" * 60)
    print("  Vector Store Documents")
    print("=" * 60)

    if store.is_empty:
        print("  Store khaali hai.")
        print("  Pehle ingest karo: python tests\\ingest_pdfs.py")
        return 1

    stats = store.stats()
    print(f"  Dimension:     {stats['dimension']}")
    print(f"  Total chunks:  {stats['total_vectors']}")
    print(f"  Documents:     {stats['unique_documents']}")
    print()

    docs = store.list_documents()
    for i, d in enumerate(docs, 1):
        pages = d["pages"]
        page_preview = f"{pages[:8]}{'...' if len(pages) > 8 else ''}"
        print(f"  [{i}] {d['file_name']}")
        print(f"       document_id:  {d['document_id']}")
        print(f"       chunks:       {d['chunks']}")
        print(f"       pages:        {len(pages)} ({page_preview})")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())