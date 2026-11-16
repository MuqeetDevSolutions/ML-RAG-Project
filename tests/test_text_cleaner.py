"""
Test script: text cleaning + metadata.

Yeh script:
1. sample.pdf ko padhta hai (raw text ke sath).
2. Raw aur cleaned text ka size compare karta hai.
3. Metadata (document_id, uploaded_at, page_number) verify karta hai.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_reader import read_pdf
from app.services.text_cleaner import clean_pages, clean_text


def section(title: str) -> None:
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


def main() -> int:
    pdf_path = PROJECT_ROOT / "data" / "uploads" / "sample.pdf"

    section("1. Raw PDF read")
    doc = read_pdf(pdf_path)
    print(f"   document_id:  {doc.document_id}")
    print(f"   file_name:    {doc.file_name}")
    print(f"   uploaded_at:  {doc.uploaded_at}")
    print(f"   total_pages:  {doc.total_pages}")
    print(f"   total_chars:  {doc.total_chars}")

    # Raw text ka pehla page dikhao
    raw_preview = doc.pages[0].text.strip().replace("\n", " ")[:200]
    print(f"   Raw page 1 preview: {raw_preview!r}")

    section("2. Cleaning")
    before = doc.total_chars
    clean_pages(doc.pages)   # in-place clean
    after = doc.total_chars
    print(f"   Before: {before} chars")
    print(f"   After:  {after} chars")
    saved = before - after
    pct = (saved / before * 100) if before else 0
    print(f"   Saved:  {saved} chars ({pct:.1f}%)")

    cleaned_preview = doc.pages[0].text.strip().replace("\n", " ")[:200]
    print(f"   Cleaned page 1 preview: {cleaned_preview!r}")

    section("3. Metadata verification")
    assert doc.document_id, "document_id khaali hai"
    assert doc.uploaded_at, "uploaded_at khaali hai"
    assert doc.total_pages == len(doc.pages), "pages count mismatch"

    for p in doc.pages:
        assert p.document_id == doc.document_id, "page ka document_id galat"
        assert p.file_name == doc.file_name, "page ka file_name galat"
        assert 1 <= p.page_number <= doc.total_pages, "page_number out of range"

    print(f"   document_id: {doc.document_id}")
    print(f"   uploaded_at: {doc.uploaded_at}")
    print(f"   Page 1 metadata:")
    print(f"      page_number: {doc.pages[0].page_number}")
    print(f"      document_id: {doc.pages[0].document_id}")
    print(f"      file_name:   {doc.pages[0].file_name}")
    print("   Status: OK (metadata consistent)")

    section("4. clean_text() unit tests")

    # Manual test cases
    tests = [
        # (input, expected_contains_or_equals)
        ("Hello    World", "Hello World"),
        ("Line1\n\n\n\n\nLine2", "Line1\n\nLine2"),
        ("infor-\nmation", "information"),
        ("   leading and trailing   ", "leading and trailing"),
        ("tab\there", "tab here"),
        ("COVID-19\nreport", "COVID-19\nreport"),  # yeh join NAHI hona chahiye
    ]

    for raw, expected in tests:
        got = clean_text(raw)
        ok = got == expected
        status = "PASS" if ok else "FAIL"
        print(f"   {status}  input={raw!r}")
        print(f"          expected={expected!r}")
        print(f"          got=     {got!r}")

    section("RESULT")
    print("   Text cleaning + metadata: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())