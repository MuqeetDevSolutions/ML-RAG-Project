"""
Test: Production features.

Verify karta hai:
  1. Logging config chal rahi (file ban gayi)
  2. Global error handlers — consistent JSON
  3. /health lightweight hai
  4. /api/status detailed info deta hai
  5. 404 handler consistent format me
  6. Validation errors consistent format me
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.logging_config import get_logger


client = TestClient(app)


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def main() -> int:
    results = []

    # ---------- 1. Logging ----------
    section("1. Logging configuration")
    logs_dir = settings.PROJECT_ROOT / "logs"
    log_file = logs_dir / "app.log"

    logger = get_logger("test.production")
    logger.info("Test log message — hello")

    print(f"   Logs dir:   {logs_dir}")
    print(f"   Logs dir exists: {logs_dir.exists()}")
    print(f"   Log file:   {log_file}")
    print(f"   Log file exists: {log_file.exists()}")
    if log_file.exists():
        size = log_file.stat().st_size
        print(f"   Log file size: {size} bytes")
        # Last 3 lines dikhao
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            print(f"   Last 2 lines:")
            for ln in lines[-2:]:
                print(f"      {ln.rstrip()[:100]}")
        except Exception as e:
            print(f"   Read error: {e}")

    ok = log_file.exists() and log_file.stat().st_size > 0
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 2. /health (lightweight) ----------
    section("2. GET /health")
    r = client.get("/health")
    print(f"   Status: {r.status_code}")
    body = r.json()
    print(f"   Body:   {body}")
    ok = r.status_code == 200 and body.get("status") == "ok"
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 3. /api/status (detailed) ----------
    section("3. GET /api/status")
    r = client.get("/api/status")
    print(f"   Status: {r.status_code}")
    body = r.json()
    print(f"   Overall: {body.get('status')}")

    checks = body.get("checks", {})
    for name, chk in checks.items():
        ok_flag = "OK" if chk.get("ok") else "FAIL"
        print(f"   [{ok_flag}] {name}")
        for k, v in chk.items():
            if k == "ok":
                continue
            print(f"        {k}: {v}")

    ok = (
        r.status_code == 200
        and body.get("status") in ("healthy", "degraded")
        and "checks" in body
    )
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 4. 404 handler ----------
    section("4. 404 error handler (consistent format)")
    r = client.get("/this-path-does-not-exist-xyz")
    print(f"   Status: {r.status_code}  (expect 404)")
    body = r.json()
    print(f"   Body:   {body}")
    ok = (
        r.status_code == 404
        and body.get("error") == "http_error"
        and "message" in body
    )
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 5. Validation error (422) ----------
    section("5. Validation error handler (consistent format)")
    # /api/ask me galat body bhejo
    r = client.post("/api/ask", json={"question": ""})
    print(f"   Status: {r.status_code}  (expect 422)")
    body = r.json()
    print(f"   Body:   {str(body)[:200]}...")
    ok = (
        r.status_code == 422
        and body.get("error") == "validation_error"
        and "message" in body
    )
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 6. Existing endpoints still work ----------
    section("6. Regression check — old endpoints")
    r1 = client.get("/api/documents")
    r2 = client.get("/api/info")
    print(f"   /api/documents: {r1.status_code}")
    print(f"   /api/info:      {r2.status_code}")
    ok = r1.status_code == 200 and r2.status_code == 200
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> PRODUCTION FEATURES THEEK HAIN.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())