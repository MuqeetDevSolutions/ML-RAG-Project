"""
Test: Query Rewriting.

Check karta hai:
  1. should_rewrite logic
  2. LLM-based rewrite (basic cases)
  3. Pipeline integration — follow-up properly handle hota hai
  4. rewrite flag response me set hota hai
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.query_rewriter import should_rewrite, rewrite_query
from app.services.rag_pipeline import RAGPipeline
from app.core.config import settings


def section(t: str) -> None:
    print()
    print("=" * 70)
    print(f"  {t}")
    print("=" * 70)


def test_should_rewrite() -> bool:
    section("1. should_rewrite logic")

    print(f"   QUERY_REWRITE_ENABLED: {settings.QUERY_REWRITE_ENABLED}")

    cases = [
        ("no history", "Who is Carl?", None, False),
        ("empty history", "Who is Carl?", [], False),
        ("1 turn only", "What about Susan?", [{"role": "user", "content": "Who is Carl?"}], False),
        ("2 turns", "What about Susan?", [
            {"role": "user", "content": "Who is Carl?"},
            {"role": "assistant", "content": "Carl is a watchmaker."},
        ], True),
    ]

    ok_all = True
    for label, q, h, expected in cases:
        got = should_rewrite(q, h)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        print(f"   {status}  {label}: expected={expected}, got={got}")
        if not ok:
            ok_all = False
    return ok_all


def test_basic_rewrite() -> bool:
    section("2. LLM-based rewrite (basic cases)")

    if not settings.QUERY_REWRITE_ENABLED:
        print("   SKIP — rewrite disabled")
        return True

    cases = [
        {
            "history": [
                {"role": "user", "content": "Who is Carl?"},
                {"role": "assistant", "content": "Carl is a watchmaker in Penzance."},
            ],
            "question": "What about Susan?",
            "should_contain": ["susan"],
        },
        {
            "history": [
                {"role": "user", "content": "Tell me about the watch."},
                {"role": "assistant", "content": "The watch allows time travel."},
            ],
            "question": "How does it work?",
            "should_contain": ["watch"],
        },
    ]

    ok_all = True
    for i, case in enumerate(cases, 1):
        t0 = time.time()
        rewritten = rewrite_query(case["question"], case["history"])
        elapsed = time.time() - t0
        rewritten_l = rewritten.lower()
        hits = [w for w in case["should_contain"] if w in rewritten_l]
        ok = len(hits) == len(case["should_contain"])
        status = "PASS" if ok else "FAIL"
        print(f"   {status}  Case {i} ({elapsed:.2f}s)")
        print(f"         Original:  {case['question']}")
        print(f"         Rewritten: {rewritten}")
        print(f"         Expected keywords: {case['should_contain']} → matched: {hits}")
        if not ok:
            ok_all = False
    return ok_all


def test_pipeline_integration() -> bool:
    section("3. Pipeline integration")

    pipe = RAGPipeline.load()
    if pipe.store.is_empty:
        print("   SKIP — store khaali")
        return True

    # Turn 1
    q1 = "Who is Carl?"
    ra1 = pipe.ask(q1)
    print(f"   Q1: {q1}")
    print(f"      Found: {ra1.found_in_documents}")
    print(f"      Rewritten: {ra1.was_rewritten}  (expected False — no history)")
    print(f"      Retrieval Q: {ra1.retrieval_query}")
    ok1 = ra1.found_in_documents and not ra1.was_rewritten

    # Build history for turn 2
    history = [
        {"role": "user", "content": q1},
        {"role": "assistant", "content": ra1.answer[:400]},
    ]

    # Turn 2 — follow-up
    q2 = "What about Susan?"
    ra2 = pipe.ask(q2, history=history)
    print()
    print(f"   Q2: {q2}")
    print(f"      Found: {ra2.found_in_documents}")
    print(f"      Rewritten: {ra2.was_rewritten}")
    print(f"      Rewritten query: {ra2.rewritten_query}")
    print(f"      Retrieval Q: {ra2.retrieval_query}")
    print(f"      Answer: {ra2.answer[:150]}...")

    # Verify: rewritten query has 'susan'
    ok2 = (
        ra2.found_in_documents
        and (ra2.was_rewritten or "susan" in ra2.retrieval_query.lower())
        and "susan" in ra2.answer.lower()
    )

    print(f"   Status: {'PASS' if ok1 and ok2 else 'FAIL'}")
    return ok1 and ok2


def test_rewrite_disabled() -> bool:
    section("4. Rewrite disabled — fallback path")

    # Temporarily disable
    old_val = settings.QUERY_REWRITE_ENABLED
    settings.QUERY_REWRITE_ENABLED = False

    try:
        history = [
            {"role": "user", "content": "Who is Carl?"},
            {"role": "assistant", "content": "Carl is a watchmaker."},
        ]
        rewritten = rewrite_query("What about Susan?", history)
        # Should be unchanged (no rewrite)
        ok = rewritten == "What about Susan?"
        print(f"   Original:  What about Susan?")
        print(f"   Rewritten: {rewritten}")
        print(f"   Status: {'PASS' if ok else 'FAIL'}")
        return ok
    finally:
        settings.QUERY_REWRITE_ENABLED = old_val


def main() -> int:
    results = [
        test_should_rewrite(),
        test_basic_rewrite(),
        test_pipeline_integration(),
        test_rewrite_disabled(),
    ]

    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> QUERY REWRITING THEEK KAAM KAR RAHI HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())