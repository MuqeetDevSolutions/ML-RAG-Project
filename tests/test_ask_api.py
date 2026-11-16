"""
Test: /api/ask endpoint (RAG through HTTP).

Test karta hai:
  1. GET /api/documents — confirm store me data hai
  2. POST /api/ask — in-document sawaal → answer + sources
  3. POST /api/ask — out-of-scope sawaal → 'not found' + koi sources nahi
  4. Validation — khaali question → 400/422 error
  5. top_k field kaam kar raha
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def section(t: str) -> None:
    print()
    print("=" * 70)
    print(f"  {t}")
    print("=" * 70)


def print_response(body: dict, max_sources: int = 4) -> None:
    print(f"   Q: {body.get('question')}")
    print(f"   A: {body.get('answer')}")
    print(f"   Found:        {body.get('found_in_documents')}")
    print(f"   Top score:    {body.get('top_score')}")
    print(f"   Retrieved:    {body.get('retrieved_count')}")
    print(f"   Elapsed:      {body.get('elapsed_seconds')}s")

    sources = body.get("sources", [])
    print(f"   Sources:      {len(sources)}")
    for i, s in enumerate(sources[:max_sources], 1):
        print(
            f"      [{i}] {s['file_name']} p{s['page_number']} "
            f"(best={s['best_score']}, chunks={s['chunk_count']})"
        )
        for c in s["chunks"][:1]:
            print(f"          → {c['preview'][:100]}...")


def main() -> int:
    results = []

    # ---------- 1. Confirm store not empty ----------
    section("1. GET /api/documents (store check)")
    r = client.get("/api/documents")
    print(f"   Status: {r.status_code}")
    body = r.json()
    print(f"   Documents: {body.get('total_documents')}")
    print(f"   Chunks:    {body.get('total_chunks')}")
    if body.get("total_documents", 0) == 0:
        print("   FAIL — store khaali hai. Pehle ingest karo:")
        print("      python tests\\ingest_pdfs.py")
        return 1
    results.append(True)

    # ---------- 2. In-document question ----------
    section("2. POST /api/ask — in-document question")
    payload = {"question": "Who is Carl?", "top_k": 5}
    r = client.post("/api/ask", json=payload)
    print(f"   Status: {r.status_code}")
    if r.status_code != 200:
        print(f"   Body: {r.text}")
        results.append(False)
    else:
        body = r.json()
        print_response(body)
        ok = (
            body.get("found_in_documents") is True
            and len(body.get("answer", "")) > 20
            and len(body.get("sources", [])) > 0
        )
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 3. Another in-document question ----------
    section("3. POST /api/ask — Laura question")
    payload = {"question": "Why is Laura invisible?", "top_k": 5}
    r = client.post("/api/ask", json=payload)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        print_response(body)
        ok = body.get("found_in_documents") is True
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        print(r.text)
        results.append(False)

    # ---------- 4. Out-of-scope question ----------
    section("4. POST /api/ask — out-of-scope (hallucination test)")
    payload = {"question": "What is the capital of France?"}
    r = client.post("/api/ask", json=payload)
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        body = r.json()
        print_response(body)
        ok = (
            body.get("found_in_documents") is False
            and len(body.get("sources", [])) == 0
        )
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        print(r.text)
        results.append(False)

    # ---------- 5. Validation — empty question ----------
    section("5. POST /api/ask — validation (empty question)")
    payload = {"question": ""}
    r = client.post("/api/ask", json=payload)
    print(f"   Status: {r.status_code}  (expect 400 or 422)")
    print(f"   Body: {r.json()}")
    ok = r.status_code in (400, 422)
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 6. Validation — top_k out of range ----------
    section("6. POST /api/ask — validation (top_k too large)")
    payload = {"question": "test", "top_k": 999}
    r = client.post("/api/ask", json=payload)
    print(f"   Status: {r.status_code}  (expect 422)")
    ok = r.status_code == 422
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 7. top_k smaller returns fewer retrieved ----------
    section("7. POST /api/ask — top_k=3")
    payload = {"question": "Who is Carl?", "top_k": 3}
    r = client.post("/api/ask", json=payload)
    if r.status_code == 200:
        body = r.json()
        print(f"   Retrieved: {body.get('retrieved_count')} (expect 3)")
        print(f"   Sources:   {len(body.get('sources', []))}")
        ok = body.get("retrieved_count") == 3
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        print(r.text)
        results.append(False)

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> ASK API THEEK KAAM KAR RAHI HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())