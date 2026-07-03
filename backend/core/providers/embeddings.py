"""
Embedding facade for RAG and vector memory.

Prefers the Hugging Face Inference API when HF_TOKEN is configured. Falls back
to a deterministic local hashing vector so ingestion and retrieval keep working
without model packages or network access.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from . import config


DEFAULT_DIMENSION = 384
_TOKEN_RE = re.compile(r"[a-zA-Z0-9_.$:/-]+")


def dimension() -> int:
    raw = config.get("PINECONE_DIMENSION") or config.get("EMBEDDING_DIMENSION")
    try:
        return max(32, min(4096, int(raw)))
    except Exception:
        return DEFAULT_DIMENSION


def embed_text(text: str, dim: int | None = None) -> list[float]:
    dim = dim or dimension()
    hf = _hf_embed(text, dim)
    if hf:
        return hf
    return _hash_embed(text, dim)


def backend() -> str:
    return "huggingface" if bool(config.get("HF_TOKEN")) else "hash"


def _hf_embed(text: str, dim: int) -> list[float] | None:
    token = config.get("HF_TOKEN")
    if not token:
        return None
    try:
        import httpx

        model = config.get("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        resp = httpx.post(
            f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model}",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": text[:2000], "options": {"wait_for_model": True}},
            timeout=30,
        )
        resp.raise_for_status()
        vec = _flatten_embedding(resp.json())
        if not vec:
            return None
        return _resize(_normalize(vec), dim)
    except Exception:
        return None


def _flatten_embedding(data) -> list[float]:
    if isinstance(data, list) and data and isinstance(data[0], (int, float)):
        return [float(v) for v in data]
    if isinstance(data, list) and data and isinstance(data[0], list):
        rows = data[0] if data and data[0] and isinstance(data[0][0], list) else data
        if not rows:
            return []
        width = len(rows[0])
        totals = [0.0] * width
        count = 0
        for row in rows:
            if isinstance(row, list):
                for i, value in enumerate(row[:width]):
                    totals[i] += float(value)
                count += 1
        return [v / max(1, count) for v in totals]
    return []


@lru_cache(maxsize=2048)
def _token_hash(token: str) -> int:
    return int(hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest(), 16)


def _hash_embed(text: str, dim: int) -> list[float]:
    vec = [0.0] * dim
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        tokens = [text[:128].lower() or "empty"]
    for token in tokens[:2048]:
        h = _token_hash(token)
        idx = h % dim
        sign = 1.0 if (h >> 7) & 1 else -1.0
        vec[idx] += sign * (1.0 + math.log1p(len(token)))
    return _normalize(vec)


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0:
        return vec
    return [v / norm for v in vec]


def _resize(vec: list[float], dim: int) -> list[float]:
    if len(vec) == dim:
        return vec
    if len(vec) > dim:
        return vec[:dim]
    return vec + [0.0] * (dim - len(vec))
