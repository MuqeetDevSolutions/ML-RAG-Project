"""
Vector store service (FAISS-based).

Kaam:
  - Chunks ke embeddings FAISS me store karna
  - Sawaal ke embedding se top-K similar chunks nikalna
  - Metadata (chunk_id, document_id, page_number, text) sath rakhna
  - Disk par save/load
  - Kisi ek document ke saare chunks delete karna

Kyun FAISS IndexFlatIP?
  Hamare embeddings L2-normalized hain (length = 1). Is liye
  inner product = cosine similarity. FAISS ka IndexFlatIP isi ke
  liye best hai — simple, exact, fast.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any
import json

import faiss
import numpy as np

from app.core.config import settings
from app.services.chunker import Chunk
from app.services.embedder import get_dimension


INDEX_FILE = "index.faiss"
METADATA_FILE = "metadata.json"


# ----------------------------------------------------------------
# Result container
# ----------------------------------------------------------------

@dataclass
class SearchResult:
    """Ek search hit ka result."""
    chunk_id: str
    document_id: str
    file_name: str
    page_number: int
    chunk_index_in_page: int
    text: str
    score: float          # cosine similarity (higher = better)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "file_name": self.file_name,
            "page_number": self.page_number,
            "chunk_index_in_page": self.chunk_index_in_page,
            "text": self.text,
            "score": self.score,
        }


# ----------------------------------------------------------------
# Main class
# ----------------------------------------------------------------

class VectorStore:
    """
    FAISS index + parallel metadata list.

    Row i in FAISS index corresponds to metadata[i].
    """

    def __init__(self, dimension: Optional[int] = None):
        self.dimension = dimension or get_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)   # inner product (== cosine)
        self.metadata: List[Dict[str, Any]] = []

    # ---------- Basics ----------

    def __len__(self) -> int:
        return self.index.ntotal

    @property
    def is_empty(self) -> bool:
        return self.index.ntotal == 0

    # ---------- Add ----------

    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray) -> int:
        """
        Chunks + unke embeddings index me daalo.

        Args:
            chunks: List[Chunk] (jo chunker se aaye)
            embeddings: numpy array shape (len(chunks), dimension)

        Returns:
            Number of chunks added.
        """
        if not chunks:
            return 0

        embeddings = np.asarray(embeddings, dtype="float32")
        if embeddings.shape[0] != len(chunks):
            raise ValueError(
                f"chunks ({len(chunks)}) aur embeddings ({embeddings.shape[0]}) "
                "ka count match nahi karta."
            )
        if embeddings.shape[1] != self.dimension:
            raise ValueError(
                f"embedding dimension {embeddings.shape[1]} != store "
                f"dimension {self.dimension}."
            )

        self.index.add(embeddings)
        for c in chunks:
            meta = c.to_metadata()
            meta["text"] = c.text          # search result me text sath chahiye
            self.metadata.append(meta)

        return len(chunks)

    # ---------- Search ----------

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[SearchResult]:
        """
        Query ke qareeb tareen top_k chunks return karo.
        """
        if self.is_empty:
            return []

        q = np.asarray(query_embedding, dtype="float32").reshape(1, -1)
        if q.shape[1] != self.dimension:
            raise ValueError(
                f"query dimension {q.shape[1]} != store dimension {self.dimension}"
            )

        k = min(top_k, self.index.ntotal)
        scores, indices = self.index.search(q, k)

        results: List[SearchResult] = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            m = self.metadata[int(idx)]
            results.append(
                SearchResult(
                    chunk_id=m["chunk_id"],
                    document_id=m["document_id"],
                    file_name=m["file_name"],
                    page_number=int(m["page_number"]),
                    chunk_index_in_page=int(m["chunk_index_in_page"]),
                    text=m["text"],
                    score=float(score),
                )
            )
        return results

    # ---------- Document management ----------

    def list_documents(self) -> List[Dict[str, Any]]:
        """
        Unique documents ki summary (document_id ke hisaab se).
        """
        summary: Dict[str, Dict[str, Any]] = {}
        for m in self.metadata:
            doc_id = m["document_id"]
            if doc_id not in summary:
                summary[doc_id] = {
                    "document_id": doc_id,
                    "file_name": m["file_name"],
                    "chunks": 0,
                    "pages": set(),
                }
            summary[doc_id]["chunks"] += 1
            summary[doc_id]["pages"].add(m["page_number"])

        out = []
        for info in summary.values():
            out.append({
                "document_id": info["document_id"],
                "file_name": info["file_name"],
                "chunks": info["chunks"],
                "pages": sorted(info["pages"]),
            })
        return out

    def delete_document(self, document_id: str) -> int:
        """
        Ek document ke saare chunks hataao (FAISS index rebuild ke zariye).

        Kyunki FAISS IndexFlat me direct "remove one id" kaam nahi karta,
        hum index ko rebuild karte hain:
          1. Saare vectors reconstruct karo.
          2. Sirf rakhne wale vectors se naya index banao.
        """
        keep_indices = [
            i for i, m in enumerate(self.metadata)
            if m["document_id"] != document_id
        ]
        removed = len(self.metadata) - len(keep_indices)
        if removed == 0:
            return 0

        if not keep_indices:
            # Sab kuch delete — khaali index
            self.index = faiss.IndexFlatIP(self.dimension)
            self.metadata = []
            return removed

        # Purane vectors nikalo
        all_vectors = self.index.reconstruct_n(0, self.index.ntotal)  # (N, dim)
        kept_vectors = all_vectors[keep_indices]
        kept_metadata = [self.metadata[i] for i in keep_indices]

        # Naya index banao
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(np.asarray(kept_vectors, dtype="float32"))
        self.metadata = kept_metadata

        return removed

    def clear(self) -> None:
        """Poora index reset karo."""
        self.index = faiss.IndexFlatIP(self.dimension)
        self.metadata = []

    # ---------- Persistence ----------

    def save(self, directory: Optional[Path] = None) -> Path:
        """
        Index aur metadata ko disk par save karo.

        Returns:
            Directory jahan save hua.
        """
        directory = Path(directory or settings.VECTORSTORE_DIR)
        directory.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(directory / INDEX_FILE))
        with open(directory / METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, ensure_ascii=False, indent=2)

        return directory

    @classmethod
    def load(cls, directory: Optional[Path] = None) -> "VectorStore":
        """
        Disk se index + metadata load karo.

        Agar files mojood nahi to khaali (empty) store return karta hai.
        """
        directory = Path(directory or settings.VECTORSTORE_DIR)
        index_path = directory / INDEX_FILE
        meta_path = directory / METADATA_FILE

        if not index_path.exists() or not meta_path.exists():
            return cls()   # khaali store

        index = faiss.read_index(str(index_path))
        with open(meta_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        store = cls(dimension=index.d)
        store.index = index
        store.metadata = metadata
        return store

    # ---------- Debug ----------

    def stats(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "total_vectors": int(self.index.ntotal),
            "unique_documents": len({m["document_id"] for m in self.metadata}),
            "unique_files": sorted({m["file_name"] for m in self.metadata}),
        }