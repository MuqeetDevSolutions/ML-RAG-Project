"""
Test: /api/chat — conversation memory.

Test karta hai:
  1. Naya chat — conversation_id create hota hai
  2. Same conversation_id ke sath follow-up — memory kaam karti hai
  3. GET /api/conversations — list
  4. GET /api/conversations/{id} — detail
  5. DELETE /api/conversations/{id} — delete
"""

import sys
import time
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


def ask(payload: dict) -> dict:
    r = client.post("/api/chat", json=payload)
    return {"status": r.status_code, "data": r.json() if r.status_code == 200 else r.text}


def main() -> int:
    results = []

    # ---------- 0. Store not empty ----------
    r = client.get("/api/documents")
    if r.json().get("total_documents", 0) == 0:
        print("   FAIL — store khaali hai. Pehle ingest chalao.")
        return 1

    # ---------- 1. First turn (no conversation_id) ----------
    section("1. First turn — no conversation_id")
    out = ask({"question": "Who is Carl?", "top_k": 5})
    print(f"   Status: {out['status']}")
    if out["status"] != 200:
        print(f"   Error: {out['data']}")
        return 1

    d1 = out["data"]
    print(f"   Conversation: {d1['conversation_id']}")
    print(f"   Turn count:   {d1['turn_count']}")
    print(f"   Answer:       {d1['answer'][:120]}...")
    print(f"   Found:        {d1['found_in_documents']}")
    print(f"   Sources:      {len(d1['sources'])}")
    print(f"   Retrieval Q:  {d1['retrieval_query']}")

    conv_id = d1["conversation_id"]
    ok = (
        out["status"] == 200
        and conv_id
        and d1["turn_count"] == 2   # 1 user + 1 assistant
        and d1["found_in_documents"]
    )
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 2. Follow-up (same conversation_id) ----------
    section("2. Follow-up — 'What about Susan?'")
    time.sleep(0.5)  # rate limit ke liye thora gap
    out = ask({
        "conversation_id": conv_id,
        "question": "What about Susan?",
        "top_k": 5,
    })
    print(f"   Status: {out['status']}")
    if out["status"] != 200:
        print(f"   Error: {out['data']}")
        results.append(False)
    else:
        d2 = out["data"]
        print(f"   Same conv id:  {d2['conversation_id'] == conv_id}")
        print(f"   Turn count:    {d2['turn_count']}  (expect 4)")
        print(f"   Retrieval Q:   {d2['retrieval_query']}")
        print(f"   Answer:        {d2['answer'][:160]}...")
        print(f"   Found:         {d2['found_in_documents']}")

        ok = (
            d2["conversation_id"] == conv_id
            and d2["turn_count"] == 4
            and d2["found_in_documents"]
            and "susan" in d2["answer"].lower()
        )
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 3. List conversations ----------
    section("3. GET /api/conversations")
    r = client.get("/api/conversations")
    print(f"   Status: {r.status_code}")
    data = r.json()
    print(f"   Total: {data['total']}")
    for c in data["conversations"][:3]:
        print(f"      - {c['conversation_id'][:8]}...  turns={c['turn_count']}")
    ok = r.status_code == 200 and data["total"] >= 1
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 4. Get conversation detail ----------
    section("4. GET /api/conversations/{id}")
    r = client.get(f"/api/conversations/{conv_id}")
    print(f"   Status: {r.status_code}")
    if r.status_code == 200:
        d = r.json()
        print(f"   Turns: {d['turn_count']}")
        for t in d["turns"]:
            role = t["role"]
            content = t["content"][:80]
            print(f"      [{role}] {content}...")
        ok = d["turn_count"] == 4
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        print(r.text)
        results.append(False)

    # ---------- 5. Delete conversation ----------
    section("5. DELETE /api/conversations/{id}")
    r = client.delete(f"/api/conversations/{conv_id}")
    print(f"   Status: {r.status_code}")
    print(f"   Body:   {r.json()}")
    ok = r.status_code == 200
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # Verify gone
    r = client.get(f"/api/conversations/{conv_id}")
    print(f"   After delete — GET status: {r.status_code} (expect 404)")
    ok = r.status_code == 404
    results.append(ok)
    print(f"   >>> {'PASS' if ok else 'FAIL'}")

    # ---------- 6. New conversation starts fresh ----------
    section("6. New conversation (no id) — fresh history")
    time.sleep(0.5)
    out = ask({"question": "Who is Carl?", "top_k": 3})
    if out["status"] == 200:
        d = out["data"]
        print(f"   New conv id: {d['conversation_id'][:8]}...")
        print(f"   Turn count:  {d['turn_count']} (expect 2 — fresh)")
        ok = d["turn_count"] == 2 and d["conversation_id"] != conv_id
        results.append(ok)
        print(f"   >>> {'PASS' if ok else 'FAIL'}")
    else:
        results.append(False)
        print(out["data"])

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for r in results if r)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> CHAT API + CONVERSATION MEMORY THEEK HAIN.")
        return 0
    print("   >>> Kuch tests fail hue.")
    return 1


if __name__ == "__main__":
    sys.exit(main())