"""
Store manager — ek hi VectorStore instance poore app me.

Kyun?
    Har HTTP request par disk se store load karna slow hai
    (427 chunks ka index.faiss ~ MB me, load ~1 sec).
    Hum ek singleton rakhte hain jo app start hote hi ek baar load hota
    hai, aur end tak reuse hota hai.

Thread safety:
    FastAPI by default single worker me chalta hai (development me).
    Production me multiple workers ho sakte hain — tab har worker
    ka apna store instance hoga. Phase 18 me hum isko address karenge.

Save:
    Jab bhi store modify ho (upload / delete), hum save() call karte hain
    taake disk par persist ho jaye.
"""

from typing import Optional
from app.services.vector_store import VectorStore


# Module-level singleton
_store: Optional[VectorStore] = None


def get_store() -> VectorStore:
    """
    Ek hi VectorStore instance return karo (singleton).

    Pehli call par disk se load hota hai, uske baad cached.
    """
    global _store
    if _store is None:
        _store = VectorStore.load()
    return _store


def save_store() -> None:
    """Store ko disk par save karo (after modifications)."""
    store = get_store()
    store.save()


def reload_store() -> VectorStore:
    """
    Disk se fresh store load karo (singleton replace karke).

    Kabhi kabhi useful jab external process ne store change kiya ho.
    """
    global _store
    _store = VectorStore.load()
    return _store