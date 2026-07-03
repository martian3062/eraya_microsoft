"""
Vector-memory backends for ErayaGraph / RAG.

- PineconeStore: managed vector store (general shared context). Enabled when
  PINECONE_API_KEY is set and the `pinecone` package is installed.
- CyborgStore: encrypted vector store for security-sensitive Guardian context.
  Enabled when CYBORGDB_API_KEY is set and the `cyborgdb` client is installed.

Both expose a tiny, uniform interface: `.ok`, `.upsert(id, vector, metadata, text)`,
`.query(vector, k)`. Anything missing -> `.ok is False`, and VectorStore falls back
to Chroma / in-memory. Never raises on import.
"""
from __future__ import annotations

import logging

from . import config

logger = logging.getLogger("eraya.providers.memory")


class PineconeStore:
    def __init__(self, domain: str, index: str | None = None):
        self.ok = False
        self.domain = domain
        self._index = None
        self._namespace = domain
        key = config.get("PINECONE_API_KEY")
        if not key:
            return
        try:
            from pinecone import Pinecone
            pc = Pinecone(api_key=key)
            self._index_name = index or config.get("PINECONE_INDEX", "eraya")
            self._index = pc.Index(self._index_name)
            self.ok = True
            logger.info("PineconeStore ready - index '%s' ns '%s'", self._index_name, domain)
        except Exception as exc:
            logger.warning("Pinecone unavailable: %s", exc)
            self.ok = False

    def upsert(self, doc_id: str, vector: list[float], metadata: dict, text: str = "") -> bool:
        if not self.ok:
            return False
        try:
            meta = {**metadata, "text": text[:2000]}
            self._index.upsert(vectors=[{"id": doc_id, "values": vector, "metadata": meta}],
                               namespace=self._namespace)
            return True
        except Exception as exc:
            logger.warning("Pinecone upsert failed: %s", exc)
            return False

    def query(self, vector: list[float], k: int = 5) -> list[dict]:
        if not self.ok:
            return []
        try:
            res = self._index.query(vector=vector, top_k=k, include_metadata=True,
                                    namespace=self._namespace)
            out = []
            for m in res.get("matches", []):
                meta = m.get("metadata", {}) or {}
                out.append({"text": meta.get("text", ""), "metadata": meta,
                            "distance": 1.0 - float(m.get("score", 0.0))})
            return out
        except Exception as exc:
            logger.warning("Pinecone query failed: %s", exc)
            return []


class CyborgStore:
    """Encrypted vector store for sensitive Guardian/KAVACHA context."""

    def __init__(self, domain: str):
        self.ok = False
        self.domain = domain
        self._index = None
        key = config.get("CYBORGDB_API_KEY")
        if not key:
            return
        try:
            import cyborgdb  # type: ignore
            client = cyborgdb.Client(api_key=key)
            self._index = client.get_or_create_index(f"eraya_{domain}")
            self.ok = True
            logger.info("CyborgStore (encrypted) ready - %s", domain)
        except Exception as exc:
            logger.warning("CyborgDB unavailable: %s", exc)
            self.ok = False

    def upsert(self, doc_id: str, vector: list[float], metadata: dict, text: str = "") -> bool:
        if not self.ok:
            return False
        try:
            self._index.upsert([{"id": doc_id, "vector": vector,
                                 "metadata": {**metadata, "text": text[:2000]}}])
            return True
        except Exception as exc:
            logger.warning("CyborgDB upsert failed: %s", exc)
            return False

    def query(self, vector: list[float], k: int = 5) -> list[dict]:
        if not self.ok:
            return []
        try:
            res = self._index.query(vector, top_k=k)
            return [{"text": (r.get("metadata") or {}).get("text", ""),
                     "metadata": r.get("metadata", {}),
                     "distance": float(r.get("distance", 1.0))} for r in res]
        except Exception as exc:
            logger.warning("CyborgDB query failed: %s", exc)
            return []
