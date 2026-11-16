"""
PDF reading service.
"""

from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List
import uuid

import pymupdf

from app.core.security import is_valid_pdf_file


MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024   # 100 MB
MAX_PAGES = 500
MIN_CHARS_PER_PAGE = 20


# ----------------------------------------------------------------
# Custom exceptions
# ----------------------------------------------------------------

class PdfProcessingError(Exception):
    """Base error class for PDF processing."""


class PdfTooLargeError(PdfProcessingError):
    """File size ya page count limit se zyada."""


class PdfEncryptedError(PdfProcessingError):
    """PDF password-protected hai."""


class PdfCorruptedError(PdfProcessingError):
    """PDF corrupt hai ya padha nahi ja sakta."""


class PdfInvalidTypeError(PdfProcessingError):
    """File PDF nahi hai (magic bytes check fail)."""


# ----------------------------------------------------------------
# Data containers
# ----------------------------------------------------------------

@dataclass
class PageText:
    page_number: int
    text: str
    char_count: int
    document_id: str
    file_name: str
    is_scanned: bool = False


@dataclass
class ExtractedDocument:
    document_id: str
    file_name: str
    file_path: str
    total_pages: int
    uploaded_at: str
    pages: List[PageText] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    scanned_pages: List[int] = field(default_factory=list)

    @property
    def total_chars(self) -> int:
        return sum(p.char_count for p in self.pages)

    @property
    def has_text(self) -> bool:
        return self.total_chars > 0

    @property
    def is_fully_scanned(self) -> bool:
        return len(self.scanned_pages) == self.total_pages


# ----------------------------------------------------------------
# Validation
# ----------------------------------------------------------------

def _validate_file(path: Path) -> None:
    """File-level checks: mojood hai, PDF hai (bytes), size theek hai."""
    if not path.exists():
        raise FileNotFoundError(f"PDF file mojood nahi: {path}")

    if not path.is_file():
        raise PdfProcessingError(f"Yeh file nahi hai: {path}")

    if path.suffix.lower() != ".pdf":
        raise PdfProcessingError(f"Yeh PDF file nahi hai: {path.name}")

    size = path.stat().st_size
    if size == 0:
        raise PdfCorruptedError(f"File khaali hai (0 bytes): {path.name}")

    if size > MAX_FILE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        raise PdfTooLargeError(
            f"File bohot bari hai ({mb:.1f} MB). "
            f"Maximum: {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
        )

    # SECURITY: Magic bytes check (extension fake ho sakti hai)
    is_valid, err = is_valid_pdf_file(path)
    if not is_valid:
        raise PdfInvalidTypeError(f"File PDF nahi hai: {err}")


def _is_low_text(text: str) -> bool:
    return len(text.strip()) < MIN_CHARS_PER_PAGE


# ----------------------------------------------------------------
# Main function
# ----------------------------------------------------------------

def read_pdf(file_path: str | Path) -> ExtractedDocument:
    path = Path(file_path)
    _validate_file(path)

    document_id = str(uuid.uuid4())
    uploaded_at = datetime.now(timezone.utc).isoformat()

    warnings: List[str] = []
    scanned_pages: List[int] = []
    pages: List[PageText] = []

    try:
        doc = pymupdf.open(path)
    except pymupdf.FileDataError as e:
        raise PdfCorruptedError(
            f"PDF corrupt hai ya padha nahi ja sakta: {path.name} ({e})"
        )
    except Exception as e:
        raise PdfCorruptedError(
            f"PDF kholte waqt error: {type(e).__name__}: {e}"
        )

    try:
        if doc.needs_pass:
            raise PdfEncryptedError(
                f"PDF password-protected hai: {path.name}. "
                "Pehle password hata kar upload karo."
            )

        total_pages = doc.page_count
        if total_pages == 0:
            raise PdfCorruptedError(f"PDF me koi page nahi: {path.name}")

        if total_pages > MAX_PAGES:
            raise PdfTooLargeError(
                f"PDF me bohot zyada pages hain ({total_pages}). "
                f"Maximum: {MAX_PAGES} pages."
            )

        for i, page in enumerate(doc, start=1):
            try:
                text = page.get_text("text") or ""
            except Exception as e:
                warnings.append(f"Page {i}: text extract nahi ho saka ({e})")
                text = ""

            low = _is_low_text(text)
            if low:
                scanned_pages.append(i)

            pages.append(
                PageText(
                    page_number=i,
                    text=text,
                    char_count=len(text),
                    document_id=document_id,
                    file_name=path.name,
                    is_scanned=low,
                )
            )
    finally:
        doc.close()

    if scanned_pages and len(scanned_pages) == total_pages:
        warnings.append(
            f"Yeh PDF poora scanned lagta hai ({total_pages} pages). "
            "OCR ke bagair is se text nahi milega."
        )
    elif scanned_pages:
        warnings.append(
            f"{len(scanned_pages)} scanned/empty page(s) mile: "
            f"{scanned_pages[:10]}{'...' if len(scanned_pages) > 10 else ''}"
        )

    total_chars = sum(p.char_count for p in pages)
    if total_chars == 0:
        warnings.append("Is PDF se koi bhi text extract nahi hua.")

    return ExtractedDocument(
        document_id=document_id,
        file_name=path.name,
        file_path=str(path.resolve()),
        total_pages=total_pages,
        uploaded_at=uploaded_at,
        pages=pages,
        warnings=warnings,
        scanned_pages=scanned_pages,
    )