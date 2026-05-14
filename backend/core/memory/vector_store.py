"""
VectorStore — semantic memory for agent context retrieval.

Uses Chroma (local dev) with optional pgvector (production).
Agents store perception results and retrieve similar past contexts.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

logger = logging.getLogger("eraya.memory.vector")


class VectorStore:
    """
    Domain-scoped vector store. Agents embed perception results
    and retrieve the k most similar past states for RAG.
    """

    def __init__(self, domain: str, collection_prefix: str = "eraya"):
        self.domain = domain
        self._collection_name = f"{collection_prefix}_{domain}"
        self._client = None
        self._collection = None
        self._embedding_fn = None
        self._fallback: list[dict[str, Any]] = []  # in-memory if Chroma unavailable
        self._init()

    def _init(self) -> None:
        try:
            import chromadb
            from django.conf import settings
            host = settings.ERAYA.get("CHROMA_HOST", "localhost")
            port = settings.ERAYA.get("CHROMA_PORT", 8001)
            self._client = chromadb.HttpClient(host=host, port=port)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"domain": self.domain},
            )
            logger.info("VectorStore: connected to Chroma — collection '%s'", self._collection_name)
        except Exception as exc:
            logger.warning("Chroma unavailable, using in-memory fallback: %s", exc)
            self._client = None

        try:
            from sentence_transformers import SentenceTransformer
            self._embedding_fn = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            logger.debug("sentence-transformers not installed — embeddings disabled")

    def store(self, text: str, metadata: dict[str, Any]) -> str:
        doc_id = str(uuid.uuid4())
        embedding = self._embed(text)

        if self._collection is not None and embedding is not None:
            try:
                self._collection.add(
                    ids=[doc_id],
                    embeddings=[embedding],
                    documents=[text],
                    metadatas=[{**metadata, "domain": self.domain, "ts": time.time()}],
                )
                return doc_id
            except Exception as exc:
                logger.warning("Chroma store failed: %s", exc)

        self._fallback.append({"id": doc_id, "text": text, "metadata": metadata})
        return doc_id

    def retrieve(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        embedding = self._embed(query)

        if self._collection is not None and embedding is not None:
            try:
                results = self._collection.query(
                    query_embeddings=[embedding], n_results=k
                )
                return [
                    {"text": doc, "metadata": meta, "distance": dist}
                    for doc, meta, dist in zip(
                        results["documents"][0],
                        results["metadatas"][0],
                        results["distances"][0],
                    )
                ]
            except Exception:
                pass

        # Fallback: naive substring match
        query_lower = query.lower()
        matches = [
            {"text": r["text"], "metadata": r["metadata"], "distance": 1.0}
            for r in self._fallback
            if query_lower in r["text"].lower()
        ]
        return matches[:k]

    def _embed(self, text: str) -> list[float] | None:
        if self._embedding_fn is None:
            return None
        try:
            return self._embedding_fn.encode(text).tolist()
        except Exception:
            return None

    def stats(self) -> dict[str, Any]:
        count = 0
        if self._collection is not None:
            try:
                count = self._collection.count()
            except Exception:
                count = len(self._fallback)
        else:
            count = len(self._fallback)
        return {
            "domain": self.domain,
            "backend": "chroma" if self._collection else "in-memory",
            "document_count": count,
        }
