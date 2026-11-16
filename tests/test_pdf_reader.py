"""
Test script: PDF reading.

Yeh script 'data/uploads/sample.pdf' ko padhta hai aur har page ka
text, uski length, aur total summary print karta hai.
"""

import sys
from pathlib import Path

# Project root ko sys.path me daalo taake 'app' package mile
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_reader import read_pdf


def main() -> int:
    pdf_path = PROJECT_ROOT / "data" / "uploads" / "sample.pdf"

    print()
    print("=" * 60)
    print("  PDF Reader Test")
    print("=" * 60)
    print(f"  Reading: {pdf_path}")
    print()

    try:
        doc = read_pdf(pdf_path)
    except Exception as e:
        print(f"  FAIL: {type(e).__name__}: {e}")
        return 1

    print(f"  File name:   {doc.file_name}")
    print(f"  Total pages: {doc.total_pages}")
    print(f"  Total chars: {doc.total_chars}")
    print()

    # Har page ka pehla 200 characters dikhao
    for page in doc.pages:
        preview = page.text.strip().replace("\n", " ")
        preview = preview[:200] + ("..." if len(preview) > 200 else "")
        print(f"  ── Page {page.page_number} ({page.char_count} chars) ──")
        print(f"     {preview if preview else '<EMPTY PAGE>'}")
        print()

    print("=" * 60)
    print("  RESULT: PDF read successfully")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())