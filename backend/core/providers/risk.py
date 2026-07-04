"""
Tier-2 (CPU) tabular + NLP facades for the Perceiver.

- TabPFNRefiner: a tabular foundation model (TabPFN 3) that refines the perceived
  state label from a rolling buffer of (feature-vector -> state) observations.
  Zero training config: TabPFN does in-context prediction. Works with the local
  `tabpfn` package or the hosted `tabpfn_client` (TABPFN_API_KEY). If neither is
  present, `predict()` returns None and the Perceiver keeps its existing result.

- hf_sentiment: sentiment via the Hugging Face Inference API (HF_TOKEN). Optional.

Everything degrades gracefully and never raises into the perception loop.
"""
from __future__ import annotations

import logging

from . import config

logger = logging.getLogger("eraya.providers.risk")


class TabPFNRefiner:
    """In-context tabular classifier over a rolling observation buffer."""

    def __init__(self, max_buffer: int = 200, min_samples: int = 30, refit_every: int = 20):
        self._X: list[list[float]] = []
        self._y: list[int] = []
        self._clf = None
        self._Cls = None
        self._ok: bool | None = None
        self._since_fit = 0
        self.max_buffer = max_buffer
        self.min_samples = min_samples
        self.refit_every = refit_every

    def _load(self) -> bool:
        if self._ok is not None:
            return self._ok
        # Prefer local tabpfn; fall back to the hosted client.
        try:
            from tabpfn import TabPFNClassifier  # type: ignore
            self._Cls = TabPFNClassifier
            self._ok = True
            return True
        except Exception:
            pass
        try:
            key = config.get("TABPFN_API_KEY")
            if not key:
                self._ok = False
                return False
            import tabpfn_client
            # Non-interactive auth: set_access_token() is the call that actually
            # authenticates a headless service (env var alone does not).
            tabpfn_client.set_access_token(key)
            from tabpfn_client import TabPFNClassifier  # type: ignore
            self._Cls = TabPFNClassifier
            self._ok = True
            return True
        except Exception as exc:
            logger.warning("TabPFN hosted client auth failed: %s", exc)
            self._ok = False
            return False

    def observe(self, features_vec, label_idx: int) -> None:
        self._X.append([float(v) for v in features_vec])
        self._y.append(int(label_idx))
        if len(self._X) > self.max_buffer:
            self._X.pop(0)
            self._y.pop(0)
        self._since_fit += 1

    def predict(self, features_vec):
        """Return (label_idx, confidence) or None if unavailable / insufficient data."""
        if not self._load():
            return None
        if len(self._X) < self.min_samples or len(set(self._y)) < 2:
            return None
        try:
            import numpy as np
            if self._clf is None or self._since_fit >= self.refit_every:
                self._clf = self._Cls()
                self._clf.fit(np.array(self._X), np.array(self._y))
                self._since_fit = 0
            proba = self._clf.predict_proba(np.array([[float(v) for v in features_vec]]))[0]
            idx = int(np.argmax(proba))
            return idx, float(proba[idx])
        except Exception as exc:
            logger.debug("TabPFN predict failed: %s", exc)
            return None


def hf_sentiment(text: str):
    """Return a sentiment score in [-1, 1] via HF Inference API, or None."""
    token = config.get("HF_TOKEN")
    if not token:
        return None
    try:
        import httpx
        model = config.get("HF_SENTIMENT_MODEL", "distilbert-base-uncased-finetuned-sst-2-english")
        resp = httpx.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {token}"},
            json={"inputs": text[:2000]},
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data[0] if isinstance(data, list) and data and isinstance(data[0], list) else data
        score = 0.0
        for r in rows:
            label = str(r.get("label", "")).upper()
            s = float(r.get("score", 0.0))
            if label.startswith("POS"):
                score += s
            elif label.startswith("NEG"):
                score -= s
        return max(-1.0, min(1.0, score))
    except Exception as exc:
        logger.debug("HF sentiment failed: %s", exc)
        return None


def available() -> dict:
    return {"tabpfn": TabPFNRefiner()._load(), "hf_sentiment": bool(config.get("HF_TOKEN"))}
