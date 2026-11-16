"""
Text chunking service.

PDF se nikla text chote chunks me todta hai taake:
  1. LLM ki context limit me fit ho jaye.
  2. Vector search accurate ho.
  3. Citations precise rahen (page number har chunk ke sath).

Strategy:
  - Har page ko ALAG chunk karte hain (page mixing nahi).
  - Ek page ke andar recursive character splitting use karte hain jo
    paragraph -> sentence -> word order me todta hai (nature-friendly).
  - Chunks ke beech overlap rakhte hain taake boundary par jumla na toote.
"""

from dataclasses import dataclass, field
from typing import List
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.pdf_reader import ExtractedDocument


# ----------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------

DEFAULT_CHUNK_SIZE = 800       # ek chunk me max characters
DEFAULT_CHUNK_OVERLAP = 150    # consecutive chunks ke beech share
MIN_CHUNK_CHARS = 30           # itne se chhote chunk ko drop kar denge


# ----------------------------------------------------------------
# Data container
# ----------------------------------------------------------------

@dataclass
class Chunk:
    """
    Ek text chunk + uski poori metadata.

    Yeh metadata RAG pipeline ke end tak travel karegi taake
    citations sahi dikha sakein.
    """
    chunk_id: str              # unique per chunk
    document_id: str           # kis PDF ka hissa hai
    file_name: str             # insaan ke padhne ke liye
    page_number: int           # kis page par tha (1-based)
    chunk_index_in_page: int   # us page ka konsa chunk (0-based)
    text: str                  # asal content
    char_count: int

    def to_metadata(self) -> dict:
        """
        Chroma / FAISS ke liye flat metadata dict.

        Vector stores me usually string/int values hi jaati hain,
        is liye yeh helper clean dict deta hai.
        """
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "file_name": self.file_name,
            "page_number": self.page_number,
            "chunk_index_in_page": self.chunk_index_in_page,
        }


# ----------------------------------------------------------------
# Splitter setup
# ----------------------------------------------------------------

def _build_splitter(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> RecursiveCharacterTextSplitter:
    """
    LangChain ka recursive splitter banata hai.

    RecursiveCharacterTextSplitter pehle paragraph ("\\n\\n") par todta
    hai, agar chunk bada rahe to sentence (". ") par, phir word (" ")
    par, aur aakhir me character par. Yeh text ko natural boundary par
    todta hai — beech se todne ke bajaye.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError(
            f"chunk_overlap ({chunk_overlap}) chunk_size "
            f"({chunk_size}) se chhota hona chahiye."
        )

    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=[
            "\n\n",   # paragraph
            "\n",     # line
            ". ",     # sentence
            "? ",
            "! ",
            "; ",
            ", ",
            " ",      # word
            "",       # character (last resort)
        ],
        keep_separator=True,
    )


# ----------------------------------------------------------------
# Main function
# ----------------------------------------------------------------

def chunk_document(
    doc: ExtractedDocument,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[Chunk]:
    """
    Ek ExtractedDocument ko chunks me todo.

    Har page ko alag chunk karte hain taake page_number sahi rahe.

    Args:
        doc: pdf_reader se mila ExtractedDocument.
        chunk_size: har chunk ka max chars.
        chunk_overlap: consecutive chunks ke beech share.

    Returns:
        List[Chunk], document ke order me.
    """
    splitter = _build_splitter(chunk_size, chunk_overlap)
    chunks: List[Chunk] = []

    for page in doc.pages:
        text = (page.text or "").strip()

        # Khaali ya scanned page ko skip karo
        if not text:
            continue

        # Us ek page ke andar split karo
        page_pieces = splitter.split_text(text)

        for idx, piece in enumerate(page_pieces):
            piece = piece.strip()

            # Bohot chhote chunk (headings etc.) skip karo
            if len(piece) < MIN_CHUNK_CHARS:
                continue

            chunks.append(
                Chunk(
                    chunk_id=str(uuid.uuid4()),
                    document_id=doc.document_id,
                    file_name=doc.file_name,
                    page_number=page.page_number,
                    chunk_index_in_page=idx,
                    text=piece,
                    char_count=len(piece),
                )
            )

    return chunks