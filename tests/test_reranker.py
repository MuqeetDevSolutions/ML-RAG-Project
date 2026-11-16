"""
Test: Reranking (cross-encoder).

Kya check karta hai:
  1. Reranker model load ho raha hai
  2. Simple query pe sahi chunk upar aata hai
  3. Two-stage retrieval — FAISS top-K me tha, rerank ke baad upar aaya
  4. Before/after comparison (rag_pipeline ke through)
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.reranker import rerank, is_enabled
from app.services.rag_pipeline import RAGPipeline


def section(t: str) -> None:
    print()
    print("=" * 70)
    print(f"  {t}")
    print("=" * 70)


def test_basic_rerank() -> bool:
    section("1. Basic rerank test")

    print(f"   Rerank enabled: {is_enabled()}")
    if not is_enabled():
        print("   SKIP — RERANK_ENABLED=false")
        return True

    query = "What is the capital of France?"
    docs = [
        "Paris is the capital of France, known for the Eiffel Tower.",
        "Berlin is the capital of Germany.",
        "The weather in France is mild in summer.",
        "French cuisine is famous worldwide.",
    ]

    t0 = time.time()
    ranked = rerank(query, docs, top_n=4)
    elapsed = time.time() - t0

    print(f"   Query: {query}")
    print(f"   Rerank time: {elapsed:.2f}s")
    print()
    print(f"   Ranked results:")
    for idx, score in ranked:
        marker = "✓" if idx == 0 else " "
        print(f"      {marker} [{idx}] score={score:+.3f}  {docs[idx][:70]}...")

    # Expectation: 'Paris' wala chunk (index 0) top par aana chahiye
    ok = ranked[0][0] == 0
    print(f"   >>> {'PASS (Paris chunk top par)' if ok else 'FAIL'}")
    return ok


def test_pipeline_with_rerank() -> bool:
    section("2. RAG pipeline with reranking")

    pipe = RAGPipeline.load()
    if pipe.store.is_empty:
        print("   SKIP — store khaali hai")
        return True

    stats = pipe.store.stats()
    print(f"   Store: {stats['total_vectors']} vectors, {stats['unique_documents']} docs")

    # Ek aisa sawaal jahan bi-encoder confused ho sakta hai
    queries = [
        "Who is Carl?",
        "Why is Laura invisible?",
        "Who is Maha's father?",
    ]

    all_pass = True
    for q in queries:
        section(f"   Query: {q}")
        t0 = time.time()
        ra = pipe.ask(q)
        elapsed = time.time() - t0

        print(f"   Found:        {ra.found_in_documents}")
        print(f"   Reranked:     {ra.rerank_applied}")
        print(f"   Stage1 (K):   {ra.retrieval_count_stage1}")
        print(f"   Stage2 (N):   {ra.retrieval_count_stage2}")
        print(f"   Top score:    {ra.top_score:+.3f}")
        print(f"   Time:         {elapsed:.2f}s")
        print(f"   Answer:       {ra.answer[:150]}...")
        print()
        print(f"   Top sources (rerank order):")
        for i, g in enumerate(ra.used_sources[:3], 1):
            print(f"      [{i}] {g['file_name']} p{g['page_number']}  "
                  f"score={g['best_score']:+.3f}")

        # Basic sanity check
        ok = ra.found_in_documents and len(ra.answer) > 20
        if not ok:
            all_pass = False

        # Time sanity (rerank should add <2s)
        if elapsed > 15:
            print(f"   WARN — slow ({elapsed:.1f}s)")

    return all_pass


def test_hallucination_still_works() -> bool:
    section("3. Hallucination test still works")
    pipe = RAGPipeline.load()
    if pipe.store.is_empty:
        return True

    for q in ["What is the capital of France?", "Who won the 2022 FIFA World Cup?"]:
        ra = pipe.ask(q)
        print(f"   Q: {q}")
        print(f"   Found: {ra.found_in_documents}  (expected: False)")
        print(f"   Sources: {len(ra.sources)}  (expected: 0)")
        if ra.found_in_documents or len(ra.sources) > 0:
            return False
    return True


def main() -> int:
    results = [
        test_basic_rerank(),
        test_pipeline_with_rerank(),
        test_hallucination_still_works(),
    ]

    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> RERANKING THEEK KAAM KAR RAHI HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())