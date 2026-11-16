"""
Test script: PDF edge cases.

Yeh script har edge case ko trigger karke dekhta hai ke hamara code
gracefully handle karta hai ya nahi:

  1. Normal PDF       -> successful read
  2. Missing file     -> FileNotFoundError
  3. Non-PDF file     -> PdfProcessingError
  4. Zero-byte file   -> PdfCorruptedError
  5. Fake PDF (text)  -> PdfCorruptedError
  6. Scanned PDF      -> read ho, lekin warning mile
"""

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.pdf_reader import (
    read_pdf,
    PdfProcessingError,
    PdfCorruptedError,
    PdfEncryptedError,
    PdfTooLargeError,
)

UPLOADS = PROJECT_ROOT / "data" / "uploads"


def section(t: str) -> None:
    print()
    print("=" * 60)
    print(f"  {t}")
    print("=" * 60)


def expect_raises(label, func, expected_exc):
    """Helper: func chalао, dekho ke expected_exc raise hoti hai."""
    try:
        func()
    except expected_exc as e:
        print(f"   PASS  {label}")
        print(f"          -> {type(e).__name__}: {e}")
        return True
    except Exception as e:
        print(f"   FAIL  {label}")
        print(f"          expected {expected_exc.__name__}, got {type(e).__name__}: {e}")
        return False
    print(f"   FAIL  {label}  (koi exception raise nahi hui)")
    return False


def main() -> int:
    results = []

    # ---------- 1. Normal PDF ----------
    section("1. Normal PDF")
    normal = UPLOADS / "sample.pdf"
    if normal.exists():
        try:
            doc = read_pdf(normal)
            print(f"   PASS  read_pdf({normal.name})")
            print(f"          pages={doc.total_pages}, chars={doc.total_chars}")
            if doc.warnings:
                print(f"          warnings: {doc.warnings}")
            results.append(True)
        except Exception as e:
            print(f"   FAIL  {type(e).__name__}: {e}")
            results.append(False)
    else:
        print(f"   SKIP  {normal.name} mojood nahi")
        results.append(True)

    # ---------- 2. Missing file ----------
    section("2. Missing file")
    results.append(
        expect_raises(
            "read_pdf(nonexistent.pdf)",
            lambda: read_pdf(UPLOADS / "nonexistent_file_xyz.pdf"),
            FileNotFoundError,
        )
    )

    # ---------- 3. Non-PDF file ----------
    section("3. Non-PDF file (wrong extension)")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Yeh plain text hai, PDF nahi.")
        tmp_txt = Path(f.name)
    try:
        results.append(
            expect_raises(
                "read_pdf(file.txt)",
                lambda: read_pdf(tmp_txt),
                PdfProcessingError,
            )
        )
    finally:
        tmp_txt.unlink(missing_ok=True)

    # ---------- 4. Zero-byte file ----------
    section("4. Zero-byte PDF")
    with tempfile.NamedTemporaryFile("wb", suffix=".pdf", delete=False) as f:
        tmp_empty = Path(f.name)
    try:
        results.append(
            expect_raises(
                "read_pdf(empty.pdf)",
                lambda: read_pdf(tmp_empty),
                PdfCorruptedError,
            )
        )
    finally:
        tmp_empty.unlink(missing_ok=True)

    # ---------- 5. Fake PDF (text with .pdf extension) ----------
    section("5. Fake PDF (text content, .pdf extension)")
    with tempfile.NamedTemporaryFile("w", suffix=".pdf", delete=False, encoding="utf-8") as f:
        f.write("Yeh asal me text hai, .pdf extension ke sath.")
        tmp_fake = Path(f.name)
    try:
        results.append(
            expect_raises(
                "read_pdf(fake.pdf)",
                lambda: read_pdf(tmp_fake),
                PdfCorruptedError,
            )
        )
    finally:
        tmp_fake.unlink(missing_ok=True)

    # ---------- 6. Scanned PDF ----------
    section("6. Scanned PDF (agar mojood ho)")
    scanned = UPLOADS / "scanned.pdf"
    if scanned.exists():
        try:
            doc = read_pdf(scanned)
            print(f"   PASS  read_pdf(scanned.pdf)")
            print(f"          pages={doc.total_pages}, chars={doc.total_chars}")
            print(f"          is_fully_scanned={doc.is_fully_scanned}")
            print(f"          has_text={doc.has_text}")
            print(f"          scanned_pages={doc.scanned_pages[:5]}{'...' if len(doc.scanned_pages)>5 else ''}")
            if doc.warnings:
                print(f"          warnings:")
                for w in doc.warnings:
                    print(f"            - {w}")
            results.append(True)
        except Exception as e:
            print(f"   FAIL  {type(e).__name__}: {e}")
            results.append(False)
    else:
        print(f"   SKIP  scanned.pdf mojood nahi (optional test)")
        results.append(True)

    # ---------- Summary ----------
    section("SUMMARY")
    total = len(results)
    passed = sum(results)
    print(f"   {passed}/{total} tests passed")
    if passed == total:
        print("   >>> SAB EDGE CASES THEEK HANDLE HO RAHE HAIN.")
        return 0
    print("   >>> KUCH TESTS FAIL HUE — upar dekho.")
    return 1


if __name__ == "__main__":
    sys.exit(main())