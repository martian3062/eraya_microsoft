"""
Public-emotion input for the quant ensemble — the crypto Fear & Greed index
(alternative.me, no key needed). Contrarian mapping: extreme fear is a buy
bias, extreme greed a sell bias. Cached ~10 min; graceful zero on failure.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger("eraya.quant.sentiment")

_cache: dict = {"ts": 0.0, "data": None}


def get_sentiment() -> dict:
    now = time.time()
    if _cache["data"] and now - _cache["ts"] < 600:
        return _cache["data"]
    data = {"live": False, "value": None, "label": "unavailable", "score": 0.0}
    try:
        import httpx
        r = httpx.get("https://api.alternative.me/fng/?limit=1", timeout=6)
        r.raise_for_status()
        row = (r.json().get("data") or [{}])[0]
        v = int(row["value"])
        score = max(-1.0, min(1.0, (50 - v) / 40.0))  # contrarian
        data = {"live": True, "value": v,
                "label": row.get("value_classification", ""), "score": round(score, 3)}
        _cache.update(ts=now, data=data)
    except Exception as exc:
        logger.warning("fear&greed fetch failed: %s", exc)
        if _cache["data"]:
            return _cache["data"]
    return data
