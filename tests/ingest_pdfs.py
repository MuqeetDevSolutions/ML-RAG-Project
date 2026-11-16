"""
Ingest script — PDFs ko vector store me daalo (incremental support).

Modes:
    python tests\\ingest_pdfs.py                  # default: append (naye add, purane rahen)
    python tests\\ingest_pdfs.py --append         # same as default
    python tests\\ingest_pdfs.py --reset          # poora store clear, phir saare PDFs dobara ingest
    python tests\\ingest_pdfs.py --list           # store me kya kya hai dikhao
    python tests\\ingest_pdfs.py --delete <id>    # ek document_id delete karo
    python tests\\ingest_pdfs.py --skip-existing  # append mode me duplicate files skip karo

Design:
- Har PDF ka SHA-ish "fingerprint" banate hain (file size + first 1KB hash)
  taake same file dobara na ingest ho.
- Append mode me sirf naye files process hote hain.
- Reset mode purana sab kuch clear kar deta hai.
"""

import sys
import time
import argparse
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.services.pdf_reader import read_pdf, PdfProcessingError
from app.services.text_cleaner import clean_pages
from app.services.chunker import chunk_document
from app.services.embedder import embed_texts
from app.services.vector_store import VectorStore


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def file_fingerprint(path: Path) -> str:
    """
    Chota fingerprint banao (file size + first 1KB ka SHA-1).

    Poori file hash karne se better — tez hai aur duplicate detection
    ke liye kaafi accurate.
    """
    size = path.stat().st_size
    h = hashlib.sha1()
    with open(path, "rb") as f:
        h.update(f.read(1024))
    return f"{size}-{h.hexdigest()[:16]}"


def get_existing_fingerprints(store: VectorStore) -> set:
    """
    Store me mojood files ke fingerprints nikalo.

    Note: metadata me hum fingerprint store nahi kar rahe abhi.
    Filhaal file_name se detect kar rahe hain. Fingerprint support
    baad me add hoga (Phase 14 me DB ke sath).
    """
    return {m.get("file_name") for m in store.metadata}


def process_pdf(pdf_path: Path) -> tuple[int, int, list]:
    """Ek PDF process karo. Returns (chunks_added, pages, warnings)."""
    t0 = time.time()

    try:
        doc = read_pdf(pdf_path)
    except PdfProcessingError as e:
        print(f"   SKIP ({type(e).__name__}): {e}")
        return 0, 0, []

    print(f"   Document ID:  {doc.document_id[:8]}...")
    print(f"   Pages:        {doc.total_pages}")
    print(f"   Raw chars:    {doc.total_chars}")

    if doc.warnings:
        for w in doc.warnings:
            print(f"   ⚠  {w}")

    clean_pages(doc.pages)
    print(f"   Cleaned chars: {doc.total_chars}")

    chunks = chunk_document(doc)
    print(f"   Chunks:       {len(chunks)}")

    if not chunks:
        print(f"   SKIP: koi chunk nahi bana")
        return 0, doc.total_pages, doc.warnings

    print(f"   Embeddings bana rahe hain ({len(chunks)} chunks)...")
    texts = [c.text for c in chunks]
    vectors = embed_texts(texts, show_progress=True)

    # Store me add karo — VectorStore ko store object pass karenge
    # Lekin process_pdf function pure hai; caller add karega.
    # Yahan hum chunks aur vectors return karenge.
    elapsed = time.time() - t0
    print(f"   Time: {elapsed:.1f}s")

    return chunks, vectors, doc.total_pages, doc.warnings


def cmd_list(store: VectorStore) -> int:
    """Store me kya kya hai dikhao."""
    section("Store contents")
    docs = store.list_documents()
    if not docs:
        print("   (khaali)")
        return 0

    print(f"   Total documents: {len(docs)}")
    print(f"   Total chunks:    {len(store)}")
    print()
    for i, d in enumerate(docs, 1):
        print(f"   [{i}] {d['file_name']}")
        print(f"       document_id: {d['document_id']}")
        print(f"       chunks:      {d['chunks']}")
        pages = d['pages']
        page_str = f"{pages[:5]}{'...' if len(pages) > 5 else ''}"
        print(f"       pages:       {page_str}")
    return 0


def cmd_delete(store: VectorStore, doc_id: str) -> int:
    """Ek document delete karo."""
    section(f"Delete: {doc_id}")

    # Pehle check karo ke exist karta hai
    docs = {d["document_id"]: d for d in store.list_documents()}
    if doc_id not in docs:
        # Maybe user ne filename diya
        by_name = {d["file_name"]: d for d in docs.values()}
        if doc_id in by_name:
            doc_id = by_name[doc_id]["document_id"]
            print(f"   Matched by filename → {doc_id}")
        else:
            print(f"   FAIL: '{doc_id}' mojood nahi")
            print(f"   Available:")
            for d in docs.values():
                print(f"      {d['document_id']}  ({d['file_name']})")
            return 1

    info = docs[doc_id]
    removed = store.delete_document(doc_id)
    print(f"   Removed {removed} chunks from '{info['file_name']}'")

    saved_to = store.save()
    print(f"   Saved to: {saved_to}")
    return 0


def cmd_ingest(store: VectorStore, reset: bool, skip_existing: bool) -> int:
    """PDFs ingest karo."""
    upload_dir = Path(settings.UPLOAD_DIR)

    section("Uploads folder")
    if not upload_dir.exists():
        print(f"   FAIL: {upload_dir} mojood nahi")
        return 1

    pdf_files = sorted(upload_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"   Koi PDF nahi mila {upload_dir} me")
        return 1

    print(f"   Folder: {upload_dir}")
    print(f"   PDFs:   {len(pdf_files)}")
    for f in pdf_files:
        size_mb = f.stat().st_size / (1024 * 1024)
        print(f"      - {f.name}  ({size_mb:.1f} MB)")

    if reset:
        section("Reset mode — store clear")
        store.clear()
        print("   Store cleared.")

    # Existing files ki list (dedupe ke liye)
    existing_names = get_existing_fingerprints(store)
    if skip_existing and existing_names:
        print(f"   Already in store: {sorted(existing_names)}")

    total_added_chunks = 0
    total_added_docs = 0
    total_pages = 0
    all_warnings = []

    for pdf_path in pdf_files:
        section(f"Processing: {pdf_path.name}")

        # Duplicate check
        if skip_existing and pdf_path.name in existing_names:
            print(f"   SKIP (already in store)")
            continue

        result = process_pdf(pdf_path)

        # process_pdf returns either (0,0,[]) on skip or (chunks, vectors, pages, warnings)
        if len(result) == 3:
            # skip case
            continue

        chunks, vectors, pages, warnings = result
        if not chunks:
            continue

        added = store.add_chunks(chunks, vectors)
        print(f"   Added to store: {added} chunks")

        total_added_chunks += added
        total_added_docs += 1
        total_pages += pages
        all_warnings.extend([f"{pdf_path.name}: {w}" for w in warnings])

    # Save
    section("Save")
    saved_to = store.save()
    print(f"   Saved to: {saved_to}")
    for f in sorted(saved_to.glob("*")):
        print(f"      {f.name}  ({f.stat().st_size / 1024:.1f} KB)")

    # Summary
    section("SUMMARY")
    print(f"   New documents: {total_added_docs}")
    print(f"   New pages:     {total_pages}")
    print(f"   New chunks:    {total_added_chunks}")
    print(f"   Store now:     {store.stats()}")

    if all_warnings:
        print(f"\n   Warnings ({len(all_warnings)}):")
        for w in all_warnings[:5]:
            print(f"      - {w}")

    print()
    print("   >>> Ab query karo:")
    print("       python tests\\query_store.py")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ingest PDFs into the vector store (incremental)."
    )
    parser.add_argument(
        "--reset", action="store_true",
        help="Poora store clear karo, phir sab dobara ingest.",
    )
    parser.add_argument(
        "--append", action="store_true",
        help="(default) Naye PDFs add karo, purane rahen.",
    )
    parser.add_argument(
        "--list", action="store_true",
        help="Store me kya kya hai dikhao.",
    )
    parser.add_argument(
        "--delete", type=str, default=None,
        help="Document ID ya filename delete karo.",
    )
    parser.add_argument(
        "--skip-existing", action="store_true",
        help="Append mode me duplicate files skip karo.",
    )

    args = parser.parse_args()

    # Store load karo
    store = VectorStore.load()

    if args.list:
        return cmd_list(store)

    if args.delete:
        return cmd_delete(store, args.delete)

    # Default ingest
    return cmd_ingest(store, reset=args.reset, skip_existing=args.skip_existing)


if __name__ == "__main__":
    sys.exit(main())