"""
Test: Frontend serve ho raha hai.

Verify karta hai:
  1. GET /          → HTML (index.html)
  2. GET /static/style.css  → CSS
  3. GET /static/app.js     → JS
  4. /docs (Swagger UI) accessible
  5. /api/info JSON return karta hai
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

    # ---------- 1. Index HTML ----------
    section("1. GET / (index.html)")
    r = client.get("/")
    print(f"   Status:      {r.status_code}")
    print(f"   Content-Type: {r.headers.get('content-type')}")
    print(f"   Length:      {len(r.text)} chars")
    has_title = "RAG Document QA" in r.text
    has_script = "/static/app.js" in r.text
    has_css = "/static/style.css" in r.text
    ok = r.status_code == 200 and has_title and has_script and has_css
    results.append(ok)
    print(f"   Contains title: {has_title}")
    print(f"   Contains app.js: {has_script}")
    print(f"   Contains style.css: {has_css}")
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 2. CSS ----------
    section("2. GET /static/style.css")
    r = client.get("/static/style.css")
    print(f"   Status:       {r.status_code}")
    print(f"   Content-Type: {r.headers.get('content-type')}")
    print(f"   Length:       {len(r.text)} chars")
    ok = r.status_code == 200 and "app-header" in r.text
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 3. JS ----------
    section("3. GET /static/app.js")
    r = client.get("/static/app.js")
    print(f"   Status:       {r.status_code}")
    print(f"   Content-Type: {r.headers.get('content-type')}")
    print(f"   Length:       {len(r.text)} chars")
    ok = r.status_code == 200 and "API_BASE" in r.text
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 4. Swagger docs ----------
    section("4. GET /docs")
    r = client.get("/docs")
    print(f"   Status: {r.status_code}")
    ok = r.status_code == 200
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 5. /api/info ----------
    section("5. GET /api/info")
    r = client.get("/api/info")
    print(f"   Status: {r.status_code}")
    print(f"   Body:   {r.json()}")
    ok = r.status_code == 200 and r.json().get("status") == "running"
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> FRONTEND THEEK SERVE HO RAHA HAI.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())