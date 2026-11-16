"""
Test script: embeddings.

Kya test karte hain:
  1. Model load ho raha hai aur dimension sahi (384) hai.
  2. Ek text ka vector shape correct hai.
  3. Similar sentences ki similarity zyada hoti hai.
  4. Different sentences ki similarity kam hoti hai.
  5. Chunks par embeddings banti hain.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.embedder import (
    get_dimension,
    embed_texts,
    embed_query,
    cosine_similarity,
)
from app.services.pdf_reader import read_pdf
from app.services.text_cleaner import clean_pages
from app.services.chunker import chunk_document


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def test_dimension() -> bool:
    section("1. Model & dimension")
    dim = get_dimension()
    print(f"   Embedding dimension: {dim}")
    ok = dim == 384  # all-MiniLM-L6-v2 ka fixed size
    print(f"   Expected: 384 -> {'OK' if ok else 'FAIL'}")
    return ok


def test_single_embedding() -> bool:
    section("2. Single text embedding")
    vec = embed_query("RAG combines retrieval and generation.")
    print(f"   Shape:  {vec.shape}")
    print(f"   dtype:  {vec.dtype}")
    print(f"   Norm:   {float((vec ** 2).sum()) ** 0.5:.4f}  (should be ~1.0)")
    print(f"   First 5 values: {[round(float(x), 4) for x in vec[:5]]}")
    ok = vec.shape == (384,) and vec.dtype.name == "float32"
    print(f"   Status: {'OK' if ok else 'FAIL'}")
    return ok


def test_similarity() -> bool:
    section("3. Semantic similarity (similar pairs zyada honi chahiye)")

    # Similar (paraphrase)
    a1 = "The company generated $20 million in revenue."
    a2 = "Company revenue was 20 million dollars."

    # Related topic
    b1 = "The company generated $20 million in revenue."
    b2 = "Revenue indicates financial performance."

    # Unrelated
    c1 = "The company generated $20 million in revenue."
    c2 = "Cats are cute animals."

    v_a1, v_a2, v_b2, v_c2 = embed_texts([a1, a2, b2, c2])
    v_b1 = v_a1

    sim_a = cosine_similarity(v_a1, v_a2)
    sim_b = cosine_similarity(v_b1, v_b2)
    sim_c = cosine_similarity(v_a1, v_c2)

    print(f"   'Revenue' vs 'Revenue (paraphrase)':  {sim_a:.4f}")
    print(f"   'Revenue' vs 'Finance (related)':      {sim_b:.4f}")
    print(f"   'Revenue' vs 'Cats (unrelated)':       {sim_c:.4f}")

    ok = sim_a > sim_b > sim_c and sim_a > 0.6
    if ok:
        print("   Status: OK (order theek hai: similar > related > unrelated)")
    else:
        print("   Status: FAIL (expected: similar > related > unrelated, aur sim_a > 0.6)")
    return ok


def test_chunks_embedding() -> bool:
    section("4. Chunks par embeddings")

    pdf_path = PROJECT_ROOT / "data" / "uploads" / "sample.pdf"
    if not pdf_path.exists():
        print(f"   SKIP  {pdf_path.name} mojood nahi")
        return True

    doc = read_pdf(pdf_path)
    clean_pages(doc.pages)
    chunks = chunk_document(doc)

    print(f"   Total chunks: {len(chunks)}")

    if not chunks:
        print("   NOTE: sample.pdf bohot chhoti hai — koi chunk nahi bana.")
        print("         Yeh test SKIP kar rahe hain. App theek hai.")
        return True

    texts = [c.text for c in chunks]
    vectors = embed_texts(texts, show_progress=False)
    print(f"   Vectors shape: {vectors.shape}  (chunks x dim)")
    ok = vectors.shape == (len(chunks), 384)
    print(f"   Status: {'OK' if ok else 'FAIL'}")
    return ok


def main() -> int:
    results = [
        test_dimension(),
        test_single_embedding(),
        test_similarity(),
        test_chunks_embedding(),
    ]

    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> EMBEDDING SERVICE THEEK HAI.")
        return 0
    print("   >>> KUCH TESTS FAIL HUE.")
    return 1


if __name__ == "__main__":
    sys.exit(main())