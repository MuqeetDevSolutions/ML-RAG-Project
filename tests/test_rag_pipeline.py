"""
Test script: Complete RAG pipeline + Smart source citations.

Yeh test:
  1. In-document sawaal — answer aur clean sources
  2. Source dedupe verification — ek page sirf ek baar dikhe
  3. Source filtering — low scores nahi dikhein
  4. Out-of-scope sawaal — hallucination test
"""

import sys
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.rag_pipeline import RAGPipeline, RAGAnswer


def section(t: str) -> None:
    print()
    print("=" * 70)
    print(f"  {t}")
    print("=" * 70)


def print_answer(ra: RAGAnswer, show_grouped: bool = True) -> None:
    print()
    print(f"  Q: {ra.question}")
    print(f"  A: {ra.answer}")
    print()
    print(f"  Top score: {ra.top_score:.4f}")
    print(f"  Found:     {ra.found_in_documents}")

    if ra.sources:
        print()
        print(f"  --- Flat sources ({len(ra.sources)}) ---")
        for i, s in enumerate(ra.sources, 1):
            print(
                f"    [{i}] {s['file_name']} p{s['page_number']} "
                f"(score={s['score']}, chunks_on_page={s['chunks_in_page']})"
            )
            print(f"        {s['preview']}")

    if show_grouped and ra.used_sources:
        print()
        print(f"  --- Grouped sources ({len(ra.used_sources)} groups) ---")
        for i, g in enumerate(ra.used_sources, 1):
            print(
                f"    [{i}] {g['file_name']} — page {g['page_number']} "
                f"(best={g['best_score']}, chunks={g['chunk_count']})"
            )
            for j, c in enumerate(g["chunks"], 1):
                print(f"        {j}) score={c['score']}  {c['preview'][:120]}...")


def check_no_duplicate_pages(ra: RAGAnswer) -> bool:
    """
    Verify karo ke (file, page) pairs unique hain flat sources me.
    """
    keys = [(s["file_name"], s["page_number"]) for s in ra.sources]
    counts = Counter(keys)
    dups = [k for k, v in counts.items() if v > 1]
    if dups:
        print(f"   FAIL — duplicate (file, page) pairs: {dups}")
        return False
    return True


def check_scores_above_threshold(ra: RAGAnswer, threshold: float = 0.35) -> bool:
    """Verify: har source ka score >= threshold hai."""
    bad = [s for s in ra.sources if s["score"] < threshold]
    if bad:
        print(f"   FAIL — kuch sources ka score < {threshold}:")
        for s in bad:
            print(f"        {s['file_name']} p{s['page_number']} score={s['score']}")
        return False
    return True


def main() -> int:
    section("RAG Pipeline Test — Smart Sources")

    pipe = RAGPipeline.load()
    if pipe.store.is_empty:
        print("  Store khaali hai. Pehle chalao:")
        print("      python tests\\ingest_pdfs.py")
        return 1

    stats = pipe.store.stats()
    print(f"  Loaded: {stats['total_vectors']} vectors, "
          f"{stats['unique_documents']} docs, files={stats['unique_files']}")

    results = []

    # ---- In-document questions ----
    questions = [
        "Who is Carl?",
        "Why is Laura invisible?",
        "Who is Maha's father?",
    ]

    for q in questions:
        section(f"Q: {q}")
        ra = pipe.ask(q)
        print_answer(ra, show_grouped=True)

        ok_answer = ra.found_in_documents and len(ra.answer) > 20
        ok_nodup = check_no_duplicate_pages(ra)
        ok_scores = check_scores_above_threshold(ra, threshold=0.35)

        overall = ok_answer and ok_nodup and ok_scores
        results.append(overall)
        print(f"  >>> Status: {'PASS' if overall else 'FAIL'} "
              f"(answer={ok_answer}, nodup={ok_nodup}, scores={ok_scores})")

    # ---- Out-of-scope ----
    section("Hallucination test")
    for q in ["What is the capital of France?",
              "Who won the 2022 FIFA World Cup?"]:
        print()
        print(f"  Q: {q}")
        ra = pipe.ask(q)
        print(f"  A: {ra.answer}")
        print(f"  Top score: {ra.top_score:.4f}")
        print(f"  Found: {ra.found_in_documents}")
        print(f"  Sources: {len(ra.sources)}")
        ok = not ra.found_in_documents and len(ra.sources) == 0
        results.append(ok)
        print(f"  >>> Status: {'PASS' if ok else 'FAIL'}")

    # ---- Summary ----
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"  {passed}/{total} tests passed")
    if passed == total:
        print("  >>> RAG PIPELINE + SMART SOURCES THEEK HAIN.")
        return 0
    print("  >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())