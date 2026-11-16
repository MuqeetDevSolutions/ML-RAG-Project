"""
Embedding service.

Yeh module text (chunks ya queries) ko fixed-size vectors me badalta hai
using sentence-transformers (all-MiniLM-L6-v2).

Design:
- Model lazy load hota hai (first call par) aur phir cached rehta hai.
  App start hone par heavy download nahi karte — sirf jab pehli baar
  embed karna ho.
- Embeddings ko L2-normalize karte hain. Isse cosine similarity aur
  inner-product search ek hi cheez ban jate hain — FAISS me kaam asaan.
"""

from typing import List, Optional
import numpy as np

from app.core.config import settings


# ----------------------------------------------------------------
# Singleton model holder
# ----------------------------------------------------------------

_model = None  # module-level global


def _get_dim_from_model(model) -> int:
    """
    Model ka embedding dimension nikaalo.

    Naye sentence-transformers versions me method ka naam
    'get_embedding_dimension' hai; purane me 'get_sentence_embedding_dimension'.
    Dono ko handle karte hain taake code kabhi na toote.
    """
    if hasattr(model, "get_embedding_dimension"):
        return model.get_embedding_dimension()
    return model.get_sentence_embedding_dimension()


def get_model():
    """
    SentenceTransformer model return karta hai (lazy load).

    Pehli baar call par model download + load hota hai (~80 MB).
    Uske baad yeh cached instance wapas milta hai.
    """
    global _model
    if _model is None:
        # Import yahan karte hain taake module import karte hi
        # heavy dependencies load na hon.
        from sentence_transformers import SentenceTransformer

        print(f"[embedder] Loading model: {settings.EMBEDDING_MODEL}")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
        dim = _get_dim_from_model(_model)
        print(f"[embedder] Model loaded. Dimension = {dim}")

    return _model


def get_dimension() -> int:
    """Embedding vector ka size (384 for all-MiniLM-L6-v2)."""
    return _get_dim_from_model(get_model())


# ----------------------------------------------------------------
# Embedding functions
# ----------------------------------------------------------------

def embed_texts(
    texts: List[str],
    batch_size: int = 32,
    normalize: bool = True,
    show_progress: bool = False,
) -> np.ndarray:
    """
    Multiple texts ko embeddings me badlo.

    Args:
        texts: list of strings
        batch_size: ek saath kitne texts process karo (memory/speed tradeoff)
        normalize: L2 normalize karo (cosine similarity ke liye haan)
        show_progress: progress bar dikhao (bade batches par helpful)

    Returns:
        numpy array shape (len(texts), dimension), dtype=float32
    """
    if not texts:
        return np.zeros((0, get_dimension()), dtype="float32")

    model = get_model()
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        convert_to_numpy=True,
        normalize_embeddings=normalize,
    )
    # FAISS float32 chahta hai
    return np.asarray(vectors, dtype="float32")


def embed_query(text: str, normalize: bool = True) -> np.ndarray:
    """
    Ek single query/text ka embedding (shape: (dimension,)).
    Convenience wrapper hai — embeddings internally 1-element list bhejta hai.
    """
    vecs = embed_texts([text], normalize=normalize, show_progress=False)
    return vecs[0]


# ----------------------------------------------------------------
# Similarity helpers (testing ke liye)
# ----------------------------------------------------------------

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Do vectors ke beech cosine similarity (-1 se 1).

    Kyunki hum embeddings ko L2-normalize karte hain, cosine similarity
    simply unka dot product hai.
    """
    a = np.asarray(a, dtype="float32")
    b = np.asarray(b, dtype="float32")
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def most_similar(query_vec: np.ndarray, candidate_vecs: np.ndarray) -> int:
    """
    Index return karta hai jo query ke sabse qareeb ho.
    (Yeh sirf demo ke liye hai — actual search Phase 5 me FAISS se hoga.)
    """
    # Normalized vectors -> dot product = cosine similarity
    scores = candidate_vecs @ query_vec
    return int(np.argmax(scores))