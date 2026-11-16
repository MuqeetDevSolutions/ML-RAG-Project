"""
Test script: chunking.

Yeh script:
1. sample.pdf read karta hai.
2. Chunks me todta hai.
3. Chunk metadata aur structure verify karta hai.
4. Ek synthetic long text par bhi chunking test karta hai.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_reader import read_pdf
from app.services.text_cleaner import clean_pages
from app.services.chunker import chunk_document, _build_splitter, MIN_CHUNK_CHARS


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def test_synthetic_text() -> bool:
    """Bina PDF ke, ek fake lambe text par splitter test karo."""
    section("1. Synthetic text chunking")

    # Ek paragraph 3 baar repeat karo taake chunk_size cross ho
    para = (
        "RAG systems combine retrieval and generation. "
        "They fetch relevant context before answering. "
        "Citations help users trust the answer. "
    )
    long_text = (para * 10).strip()   # ~1600 chars

    splitter = _build_splitter(chunk_size=400, chunk_overlap=80)
    pieces = splitter.split_text(long_text)

    print(f"   Input length: {len(long_text)} chars")
    print(f"   Chunks created: {len(pieces)}")
    print(f"   Chunk sizes: {[len(p) for p in pieces]}")

    ok = True
    # 1) Chunk size limit respect ho
    for i, p in enumerate(pieces):
        if len(p) > 400:
            print(f"   FAIL  chunk {i} bada hai: {len(p)} > 400")
            ok = False
    # 2) Ek se zyada chunk bane
    if len(pieces) < 2:
        print("   FAIL  expected 2+ chunks")
        ok = False
    # 3) Overlap kaam kar raha ho (chunk boundaries share karte hain)
    if len(pieces) >= 2:
        tail = pieces[0][-50:]
        head = pieces[1][:80]
        # Overlap ke wajah se tail ka kuch hissa head me milna chahiye
        shared = any(tail[i:i+20] in head for i in range(0, len(tail)-20, 5))
        if shared:
            print(f"   OK    overlap detected")
        else:
            print(f"   WARN  overlap detect nahi hua (ho sakta hai sentence boundary par toota ho)")

    if ok:
        print("   Status: OK")
    return ok


def test_pdf_chunking() -> bool:
    """Asli PDF par chunking test karo."""
    section("2. PDF chunking (sample.pdf)")

    pdf_path = PROJECT_ROOT / "data" / "uploads" / "sample.pdf"
    if not pdf_path.exists():
        print(f"   SKIP  {pdf_path.name} mojood nahi")
        return True

    doc = read_pdf(pdf_path)
    clean_pages(doc.pages)
    chunks = chunk_document(doc)

    print(f"   Document ID:  {doc.document_id}")
    print(f"   File name:    {doc.file_name}")
    print(f"   Total pages:  {doc.total_pages}")
    print(f"   Total chunks: {len(chunks)}")

    if chunks:
        print()
        for c in chunks:
            preview = c.text.replace("\n", " ")[:100]
            print(f"   Chunk {c.chunk_index_in_page} | "
                  f"Page {c.page_number} | "
                  f"{c.char_count} chars")
            print(f"      {preview}...")
    else:
        print("   NOTE: koi chunk nahi bana (shayad PDF bohot chhoti hai)")
        print(f"         MIN_CHUNK_CHARS = {MIN_CHUNK_CHARS}")

    # Metadata consistency verify
    section("3. Metadata verification")
    ok = True
    seen_ids = set()
    for c in chunks:
        if c.document_id != doc.document_id:
            print(f"   FAIL  chunk document_id mismatch: {c.chunk_id}")
            ok = False
        if c.file_name != doc.file_name:
            print(f"   FAIL  chunk file_name mismatch: {c.chunk_id}")
            ok = False
        if not (1 <= c.page_number <= doc.total_pages):
            print(f"   FAIL  chunk page_number out of range: {c.page_number}")
            ok = False
        if c.chunk_id in seen_ids:
            print(f"   FAIL  duplicate chunk_id: {c.chunk_id}")
            ok = False
        seen_ids.add(c.chunk_id)

    if ok:
        print("   Status: OK (saare chunks ki metadata consistent hai)")

    # to_metadata() test
    section("4. to_metadata() check")
    if chunks:
        md = chunks[0].to_metadata()
        print(f"   Sample metadata: {md}")
        required_keys = {
            "chunk_id", "document_id", "file_name",
            "page_number", "chunk_index_in_page",
        }
        missing = required_keys - set(md.keys())
        if missing:
            print(f"   FAIL  missing keys: {missing}")
            ok = False
        else:
            print("   Status: OK (saari required keys mojood)")
    else:
        print("   SKIP  koi chunk nahi")

    return ok


def main() -> int:
    results = [
        test_synthetic_text(),
        test_pdf_chunking(),
    ]

    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> CHUNKING SERVICE THEEK HAI.")
        return 0
    print("   >>> KUCH TESTS FAIL HUE.")
    return 1


if __name__ == "__main__":
    sys.exit(main())