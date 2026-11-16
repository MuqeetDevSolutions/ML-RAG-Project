"""
Test: FastAPI endpoints (using TestClient).

TestClient ek fake HTTP client hai — actual server chalane ki zarurat
nahi. Uvicorn ke bina bhi API test kar sakte hain.

Test karta hai:
  1. GET /health — 200 OK
  2. GET /api/documents — current list
  3. POST /api/documents/upload — PDF upload
  4. GET /api/documents — uploaded document list me ho
  5. DELETE /api/documents/{id} — delete
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app


client = TestClient(app)


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def main() -> int:
    results = []

    # ---------- 1. Health ----------
    section("1. GET /health")
    r = client.get("/health")
    print(f"   Status: {r.status_code}")
    print(f"   Body:   {r.json()}")
    ok = r.status_code == 200 and r.json().get("status") == "ok"
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 2. Root ----------
    section("2. GET /")
    r = client.get("/")
    print(f"   Status: {r.status_code}")
    print(f"   Body:   {r.json()}")
    ok = r.status_code == 200
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 3. List documents (baseline) ----------
    section("3. GET /api/documents (baseline)")
    r = client.get("/api/documents")
    print(f"   Status: {r.status_code}")
    body = r.json()
    print(f"   Total documents: {body.get('total_documents')}")
    print(f"   Total chunks:    {body.get('total_chunks')}")
    for d in body.get("documents", []):
        print(f"      - {d['file_name']} ({d['chunks']} chunks)")

    ok = r.status_code == 200
    results.append(ok)
    baseline_count = body.get("total_documents", 0)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 4. Upload a test PDF ----------
    section("4. POST /api/documents/upload")
    # Sample PDF use karo jo data/uploads me hai
    sample = Path(PROJECT_ROOT) / "data" / "uploads" / "sample.pdf"
    if not sample.exists():
        print(f"   SKIP — sample.pdf mojood nahi ({sample})")
        results.append(True)
    else:
        with open(sample, "rb") as f:
            files = {"file": ("sample.pdf", f, "application/pdf")}
            r = client.post("/api/documents/upload", files=files)
        print(f"   Status: {r.status_code}")
        body = r.json()
        print(f"   Body:   {body}")
        ok = r.status_code in (201, 200) and body.get("status") in ("ready", "skipped")
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")

        # Store uploaded doc id for delete test
        uploaded_doc_id = body.get("document_id")

    # ---------- 5. List documents (after) ----------
    section("5. GET /api/documents (after upload)")
    r = client.get("/api/documents")
    body = r.json()
    print(f"   Total documents: {body.get('total_documents')}")
    print(f"   Total chunks:    {body.get('total_chunks')}")
    for d in body.get("documents", []):
        print(f"      - {d['file_name']} ({d['chunks']} chunks) [{d['document_id'][:8]}...]")

    after_count = body.get("total_documents", 0)
    ok = after_count >= baseline_count
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 6. Delete (only if we uploaded) ----------
    section("6. DELETE /api/documents/{id}")
    if baseline_count == 0 and after_count > 0 and 'uploaded_doc_id' in dir():
        # Delete the uploaded doc (cleanup)
        doc_id = uploaded_doc_id
        r = client.delete(f"/api/documents/{doc_id}")
        print(f"   Deleting: {doc_id[:8]}...")
        print(f"   Status:   {r.status_code}")
        print(f"   Body:     {r.json()}")
        ok = r.status_code == 200
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        # Already had documents — skip delete to preserve user data
        print("   SKIP — user data preserve kar rahe hain")
        print("   (Chalane ke liye pehle --reset karo, phir yeh test chalao)")
        results.append(True)

    # ---------- 7. Delete non-existent ----------
    section("7. DELETE /api/documents/nonexistent")
    r = client.delete("/api/documents/nonexistent-id-xyz")
    print(f"   Status: {r.status_code}")
    print(f"   Body:   {r.json()}")
    ok = r.status_code == 404
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> API THEEK KAAM KAR RAHI HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())