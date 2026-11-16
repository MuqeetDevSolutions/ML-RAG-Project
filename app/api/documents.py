"""
Documents API — PDF upload, list, delete.

Security:
    - Filename sanitization (path traversal prevent)
    - Magic bytes check (pdf_reader)
    - Rate limiting per IP
    - File cleanup on delete
"""

import time
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Request

from app.core.config import settings
from app.core.security import (
    sanitize_filename,
    get_client_ip,
    upload_limiter,
)
from app.schemas import (
    UploadResponse,
    ListDocumentsResponse,
    DocumentInfo,
    DeleteResponse,
)
from app.services.store_manager import get_store, save_store
from app.services.pdf_reader import (
    read_pdf,
    PdfProcessingError,
    PdfTooLargeError,
    PdfEncryptedError,
    PdfCorruptedError,
    PdfInvalidTypeError,
)
from app.services.text_cleaner import clean_pages
from app.services.chunker import chunk_document
from app.services.embedder import embed_texts

from app.db.session import SessionLocal
from app.db import repositories as repo


router = APIRouter(prefix="/api/documents", tags=["documents"])


# ----------------------------------------------------------------
# Upload
# ----------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse,
             status_code=status.HTTP_201_CREATED)
async def upload_document(request: Request, file: UploadFile = File(...)):
    # ---- Rate limit ----
    client_ip = get_client_ip(request)
    allowed, retry_after = upload_limiter.check(f"upload:{client_ip}")
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. {retry_after}s baad try karo.",
            headers={"Retry-After": str(retry_after)},
        )

    t0 = time.time()

    # ---- Extension check ----
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sirf .pdf files supported hain.",
        )

    # ---- Sanitize filename ----
    safe_name = sanitize_filename(file.filename)
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest_path = upload_dir / safe_name

    # ---- Save file ----
    try:
        with open(dest_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(500, f"File save error: {e}")
    finally:
        await file.close()

    size_bytes = dest_path.stat().st_size

    # ---- Process PDF (magic bytes check inside) ----
    try:
        doc = read_pdf(dest_path)
    except PdfInvalidTypeError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File PDF nahi hai: {e}",
        )
    except PdfTooLargeError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(413, str(e))
    except PdfEncryptedError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    except PdfCorruptedError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    except PdfProcessingError as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    except Exception as e:
        dest_path.unlink(missing_ok=True)
        raise HTTPException(500, f"PDF error: {type(e).__name__}: {e}")

    # ---- Clean + chunk ----
    clean_pages(doc.pages)
    chunks = chunk_document(doc)

    if not chunks:
        dest_path.unlink(missing_ok=True)
        return UploadResponse(
            status="skipped",
            message="PDF me koi usable text nahi mila (shayad scanned hai).",
            file_name=safe_name,
            total_pages=doc.total_pages,
            warnings=doc.warnings,
            elapsed_seconds=round(time.time() - t0, 2),
        )

    # ---- Embed ----
    try:
        texts = [c.text for c in chunks]
        vectors = embed_texts(texts, show_progress=False)
    except Exception as e:
        raise HTTPException(500, f"Embeddings error: {e}")

    # ---- Store ----
    store = get_store()
    added = store.add_chunks(chunks, vectors)
    save_store()

    # ---- DB metadata ----
    with SessionLocal() as db:
        repo.upsert_document(
            db,
            document_id=doc.document_id,
            file_name=safe_name,
            file_path=str(dest_path),
            size_bytes=size_bytes,
            total_pages=doc.total_pages,
            chunk_count=added,
        )
        db.commit()

    elapsed = round(time.time() - t0, 2)

    return UploadResponse(
        status="ready",
        message=f"PDF processed — {added} chunks add hue.",
        document_id=doc.document_id,
        file_name=safe_name,
        total_pages=doc.total_pages,
        chunks_added=added,
        warnings=doc.warnings,
        elapsed_seconds=elapsed,
    )


# ----------------------------------------------------------------
# List
# ----------------------------------------------------------------

@router.get("", response_model=ListDocumentsResponse)
def list_documents():
    store = get_store()
    docs = store.list_documents()

    with SessionLocal() as db:
        db_docs = {d.document_id: d for d in repo.list_documents_db(db)}

    return ListDocumentsResponse(
        total_documents=len(docs),
        total_chunks=len(store),
        documents=[
            DocumentInfo(
                document_id=d["document_id"],
                file_name=d["file_name"],
                chunks=d["chunks"],
                pages=d["pages"],
            )
            for d in docs
        ],
    )


# ----------------------------------------------------------------
# Delete
# ----------------------------------------------------------------

@router.delete("/{document_id}", response_model=DeleteResponse)
def delete_document(document_id: str):
    store = get_store()

    existing = {d["document_id"] for d in store.list_documents()}
    if document_id not in existing:
        raise HTTPException(404, f"Document '{document_id}' nahi mila.")

    # ---- Get file path from DB before delete ----
    file_path: Path | None = None
    with SessionLocal() as db:
        doc_row = repo.get_document(db, document_id)
        if doc_row and doc_row.file_path:
            file_path = Path(doc_row.file_path)

    # ---- FAISS ----
    removed = store.delete_document(document_id)
    save_store()

    # ---- DB ----
    with SessionLocal() as db:
        repo.delete_document_db(db, document_id)
        db.commit()

    # ---- SECURITY: File delete (disk se) ----
    file_deleted = False
    if file_path and file_path.exists():
        try:
            # Safety: sirf uploads folder ke andar wali file delete karo
            upload_dir = Path(settings.UPLOAD_DIR).resolve()
            resolved = file_path.resolve()
            if upload_dir in resolved.parents or resolved.parent == upload_dir:
                resolved.unlink()
                file_deleted = True
            else:
                print(f"[delete] Skipping unsafe path: {file_path}")
        except Exception as e:
            print(f"[delete] File cleanup error: {e}")

    msg = f"{removed} chunks delete ho gaye."
    if file_deleted:
        msg += " File bhi disk se hataayi gayi."

    return DeleteResponse(
        status="deleted",
        message=msg,
        document_id=document_id,
        chunks_removed=removed,
    )