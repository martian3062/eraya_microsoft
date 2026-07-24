"""
Live CSPR/USDT market-data feed with a graceful multi-exchange cascade.

Order: Gate.io -> KuCoin -> CoinGecko (5-min points) -> synthetic random walk
anchored to the last known price. Every candle list is normalized to
[{"t": unix_s, "o", "h", "l", "c", "v"}] oldest-first. Responses are cached
~25s so autopilot ticks and UI polling share one upstream call.
"""
from __future__ import annotations

import logging
import math
import random
import time

logger = logging.getLogger("eraya.quant.feed")

_CACHE: dict = {"ts": 0.0, "data": None}
_CACHE_TTL_S = 25


def _gate(limit: int) -> list[dict]:
    import httpx
    resp = httpx.get(
        "https://api.gateio.ws/api/v4/spot/candlesticks",
        params={"currency_pair": "CSPR_USDT", "interval": "1m", "limit": limit},
        timeout=8,
    )
    resp.raise_for_status()
    rows = resp.json()
    # Gate v4: [ts, quote_vol, close, high, low, open, base_vol, closed]
    return [
        {"t": int(r[0]), "o": float(r[5]), "h": float(r[3]), "l": float(r[4]),
         "c": float(r[2]), "v": float(r[6])}
        for r in rows
    ]


def _kucoin(limit: int) -> list[dict]:
    import httpx
    resp = httpx.get(
        "https://api.kucoin.com/api/v1/market/candles",
        params={"symbol": "CSPR-USDT", "type": "1min"},
        timeout=8,
    )
    resp.raise_for_status()
    rows = resp.json().get("data") or []
    # KuCoin: [ts, open, close, high, low, volume, turnover], newest first
    out = [
        {"t": int(r[0]), "o": float(r[1]), "h": float(r[3]), "l": float(r[4]),
         "c": float(r[2]), "v": float(r[5])}
        for r in rows[:limit]
    ]
    return list(reversed(out))


def _coingecko(limit: int) -> list[dict]:
    import httpx
    resp = httpx.get(
        "https://api.coingecko.com/api/v3/coins/casper-network/market_chart",
        params={"vs_currency": "usd", "days": 1},
        timeout=10,
    )
    resp.raise_for_status()
    prices = resp.json().get("prices") or []  # [[ms, price], ...] ~5-min step
    out = []
    prev = None
    for ms, price in prices[-limit:]:
        price = float(price)
        o = prev if prev is not None else price
        out.append({"t": int(ms / 1000), "o": o, "h": max(o, price),
                    "l": min(o, price), "c": price, "v": 0.0})
        prev = price
    return out


def _synthetic(limit: int) -> list[dict]:
    """Random walk anchored to the live spot price (or its cached fallback)."""
    from core.casper.onchain import cspr_price_usd
    price = cspr_price_usd()
    now = int(time.time())
    out = []
    for i in range(limit):
        drift = price * random.gauss(0, 0.0012)
        o = price
        price = max(price + drift, price * 0.5)
        out.append({"t": now - (limit - i) * 60, "o": o,
                    "h": max(o, price), "l": min(o, price), "c": price, "v": 0.0})
    return out


def get_candles(limit: int = 180) -> dict:
    """Return {source, live, candles} — cached, cascading across sources."""
    now = time.time()
    cached = _CACHE["data"]
    if cached and now - _CACHE["ts"] < _CACHE_TTL_S:
        return cached

    for name, fn, live in (("gate.io", _gate, True), ("kucoin", _kucoin, True),
                           ("coingecko", _coingecko, True)):
        try:
            candles = fn(limit)
            if len(candles) >= 30:
                data = {"source": name, "live": live, "candles": candles}
                _CACHE.update(ts=now, data=data)
                return data
        except Exception as exc:
            logger.warning("feed %s failed: %s", name, exc)

    if cached:  # stale beats synthetic
        return cached
    data = {"source": "synthetic", "live": False, "candles": _synthetic(limit)}
    _CACHE.update(ts=now, data=data)
    return data


def spot_price() -> float:
    candles = get_candles()["candles"]
    return candles[-1]["c"] if candles else 0.0
