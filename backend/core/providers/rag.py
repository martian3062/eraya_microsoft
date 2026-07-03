"""
RAG spine for ERAYA provider integrations.

This is the runtime path for Phase 1:
    web URL -> ingestion facade -> VectorStore -> Pinecone/Chroma/in-memory
"""
from __future__ import annotations

import time
from typing import Any

from core.memory import VectorStore

from . import embeddings, ingestion


def ingest_url(domain: str, url: str, query: str | None = None) -> dict[str, Any]:
    if not url or not str(url).startswith(("http://", "https://")):
        return {"ok": False, "error": "A valid http(s) url is required."}

    fetched = ingestion.fetch_markdown(url)
    if not fetched:
        return {"ok": False, "error": "No ingestion provider could fetch the URL."}

    text = fetched.get("markdown") or ""
    if query:
        structured = ingestion.extract_structured(url, query)
        if structured is not None:
            text = f"{text}\n\nStructured extraction:\n{structured}"

    store = VectorStore(domain)
    doc_id = store.store(
        text[:20000],
        {
            "kind": "web_ingestion",
            "url": url,
            "source": fetched.get("source", "unknown"),
            "query": query or "",
            "embedding_backend": embeddings.backend(),
            "stored_at": time.time(),
        },
    )
    return {
        "ok": True,
        "domain": domain,
        "doc_id": doc_id,
        "source": fetched.get("source", "unknown"),
        "chars": len(text),
        "memory": store.stats(),
    }


def query(domain: str, text: str, k: int = 5) -> dict[str, Any]:
    if not text:
        return {"ok": False, "error": "A query string is required."}
    store = VectorStore(domain)
    hits = store.retrieve(text, max(1, min(20, int(k or 5))))
    return {
        "ok": True,
        "domain": domain,
        "query": text,
        "memory": store.stats(),
        "hits": hits,
    }
