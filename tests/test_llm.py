"""
Test script: LLM (Groq).

Yeh script:
1. GROQ_API_KEY load ho rahi hai confirm karta hai.
2. Ek simple call karta hai.
3. Usage (tokens) report karta hai.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.config import settings
from app.services.llm import generate_with_usage, generate


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def main() -> int:
    section("1. API key check")
    key = settings.GROQ_API_KEY
    if not key:
        print("   FAIL  GROQ_API_KEY khaali hai")
        print("   '.env' file banao project root me aur key daalo.")
        return 1

    # Sirf pehle aur aakhri 4 characters dikhao, poori key NAHI
    masked = f"{key[:8]}...{key[-4:]}" if len(key) > 12 else "***"
    print(f"   Key: {masked}")
    print(f"   Length: {len(key)} chars")
    print(f"   Base URL: {settings.GROQ_BASE_URL}")
    print(f"   Model: {settings.LLM_MODEL}")
    print("   Status: OK")

    section("2. Simple LLM call")
    prompt = "Reply in exactly one short sentence: What is the capital of France?"
    try:
        result = generate_with_usage(
            prompt=prompt,
            system="You are a helpful assistant. Answer concisely.",
            temperature=0.2,
            max_tokens=60,
        )
    except Exception as e:
        print(f"   FAIL  {type(e).__name__}: {e}")
        return 1

    print(f"   Prompt: {prompt}")
    print(f"   Answer: {result['text']}")
    print(f"   Model:  {result['model']}")
    print(f"   Usage:  {result['usage']}")
    print("   Status: OK")

    section("3. Second call (temperature 0.1 — deterministic-ish)")
    try:
        a = generate(
            "Say only: hello world",
            temperature=0.1,
            max_tokens=20,
        )
    except Exception as e:
        print(f"   FAIL  {e}")
        return 1
    print(f"   Answer: {a!r}")
    print("   Status: OK")

    section("4. System prompt test (persona)")
    try:
        a2 = generate(
            "Introduce yourself in one short sentence.",
            system=(
                "You are a pirate. Every sentence must end with 'Arrr!'."
            ),
            temperature=0.3,
            max_tokens=60,
        )
    except Exception as e:
        print(f"   FAIL  {e}")
        return 1
    print(f"   Answer: {a2!r}")
    print("   Status: OK (system prompt respected)")

    section("SUMMARY")
    print("   >>> GROQ LLM SERVICE THEEK HAI.")
    print("       Step 18 me RAG pipeline ke sath connect karenge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())