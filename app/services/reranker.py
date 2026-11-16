"""
Reranker — cross-encoder based reranking.

Kya karta hai?
    Bi-encoder (all-MiniLM) fast hai lekin accurate nahi. Cross-encoder
    query + chunk dono ko ek saath padhta hai aur **relevance score**
    deta hai — top results me bara farq padta hai.

Two-stage retrieval:
    Stage 1: FAISS bi-encoder → top-20 candidates (fast)
    Stage 2: Cross-encoder      → top-8 best (accurate)

Model:
    cross-encoder/ms-marco-MiniLM-L-6-v2  (~80 MB, free, local)
    MS MARCO dataset par trained — passage ranking ke liye best.

Design:
    Lazy singleton — pehli call par load, phir cached.
"""

from typing import List, Optional, Tuple

from app.core.config import settings


_model = None  # singleton


def _load_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder

        print(f"[reranker] Loading model: {settings.RERANK_MODEL}")
        _model = CrossEncoder(settings.RERANK_MODEL, max_length=512)
        print(f"[reranker] Model loaded.")
    return _model


def is_enabled() -> bool:
    return settings.RERANK_ENABLED


def rerank(
    query: str,
    documents: List[str],
    top_n: Optional[int] = None,
) -> List[Tuple[int, float]]:
    """
    Query ke against documents ko rerank karo.

    Args:
        query: user ka sawaal.
        documents: list of chunk texts.
        top_n: kitne top chunks return karne hain (None = sab).

    Returns:
        List of (original_index, score) tuples, sorted by score desc.
        Score zyada = zyada relevant.
    """
    if not documents:
        return []

    model = _load_model()

    # CrossEncoder ke liye pairs banao: [(query, doc1), (query, doc2), ...]
    pairs = [(query, doc) for doc in documents]

    # Predict scores (numpy array of floats)
    scores = model.predict(pairs, show_progress_bar=False)

    # (idx, score) tuple banao aur sort karo
    indexed = [(i, float(s)) for i, s in enumerate(scores)]
    indexed.sort(key=lambda x: x[1], reverse=True)

    if top_n is not None:
        indexed = indexed[:top_n]

    return indexed