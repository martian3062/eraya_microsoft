"""
Statistical network-anomaly detectors for KAVACHA (Tor-technique lineage).

The techniques used to study the Tor network — Onionoo relay-health monitoring,
flow/timing correlation, relay-family Sybil clustering, and OONI-style anomaly
baselining — map directly onto Casper on-chain telemetry:

    Tor technique                     -> Casper on-chain equivalent
    ------------------------------------------------------------------
    OONI baselining (z-score/entropy) -> rolling baselines on mempool/gas/liquidity
    flow / timing correlation         -> MEV / sandwich detection in the mempool
    relay-family Sybil clustering     -> governance Sybil / vote-concentration
    Onionoo relay-health / consensus  -> validator decentralization (Gini, Nakamoto)

Pure Python + numpy (already pinned). Runs unchanged on demo OR live
CasperMCPClient data. Detectors are defensive: thin/missing fields degrade to a
neutral result rather than raising. Findings are plain dicts shaped for the
`Threat` dataclass in core.agents.threat_scanner (no import cycle).
"""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from typing import Any

import numpy as np


# ─── statistical primitives ───────────────────────────────────────────────────

def gini(values: list[float]) -> float:
    """Gini coefficient of concentration (0 = even, 1 = fully concentrated)."""
    arr = np.array([v for v in values if v is not None], dtype=float)
    if arr.size == 0 or arr.sum() <= 0:
        return 0.0
    arr = np.sort(np.clip(arr, 0, None))
    n = arr.size
    cum = np.cumsum(arr)
    return float((n + 1 - 2 * (cum.sum() / cum[-1])) / n)


def shannon_entropy(counts: list[float]) -> float:
    """Normalised Shannon entropy in [0, 1] (1 = uniform, 0 = single bucket)."""
    arr = np.array([c for c in counts if c is not None], dtype=float)
    total = arr.sum()
    if total <= 0 or arr.size <= 1:
        return 0.0
    p = arr[arr > 0] / total
    h = -np.sum(p * np.log2(p))
    return float(h / math.log2(arr.size))


def nakamoto_coefficient(stakes: list[float], threshold: float = 0.5) -> int:
    """Minimum number of entities that together control > `threshold` of stake."""
    arr = np.sort(np.array([s for s in stakes if s], dtype=float))[::-1]
    total = arr.sum()
    if total <= 0:
        return 0
    cum = 0.0
    for i, s in enumerate(arr, 1):
        cum += s
        if cum / total > threshold:
            return i
    return int(arr.size)


# ─── rolling baseline (OONI-style) ─────────────────────────────────────────────

class RollingBaseline:
    """Per-metric rolling window with EWMA, z-score and windowed entropy."""

    def __init__(self, window: int = 64, alpha: float = 0.3):
        self._win: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
        self._ewma: dict[str, float] = {}
        self.alpha = alpha

    def update(self, metric: str, value: float) -> None:
        v = float(value)
        self._win[metric].append(v)
        prev = self._ewma.get(metric, v)
        self._ewma[metric] = self.alpha * v + (1 - self.alpha) * prev

    def zscore(self, metric: str, value: float) -> float:
        arr = np.array(self._win.get(metric, ()), dtype=float)
        if arr.size < 8:
            return 0.0
        mu, sd = float(arr.mean()), float(arr.std())
        if sd < 1e-9:
            return 0.0
        return (float(value) - mu) / sd

    def entropy(self, metric: str, bins: int = 8) -> float:
        arr = np.array(self._win.get(metric, ()), dtype=float)
        if arr.size < 8:
            return 1.0
        hist, _ = np.histogram(arr, bins=bins)
        return shannon_entropy(list(hist))


# ─── detectors ─────────────────────────────────────────────────────────────────

def detect_mev(pending_deploys: list[dict[str, Any]]) -> dict | None:
    """Flow/timing-correlation analog: cluster same-pool swaps by ordering and
    slippage tolerance to score sandwich / front-running risk."""
    swaps = [d for d in (pending_deploys or []) if d.get("type") == "swap"]
    if not swaps:
        return None
    by_pool: dict[str, list[dict]] = defaultdict(list)
    for d in swaps:
        by_pool[d.get("pool", "?")].append(d)

    worst = None
    for pool, group in by_pool.items():
        slippages = [float(d.get("max_slippage_bps", 0)) for d in group]
        max_slip = max(slippages)
        # Two+ high-slippage swaps queued on one pool = classic sandwich setup.
        clustered = sum(1 for s in slippages if s > 100)
        score = min(1.0, (max_slip / 300.0) + 0.25 * max(0, clustered - 1))
        if max_slip > 100 and (worst is None or score > worst["severity"]):
            worst = {
                "type": "mev_sandwich",
                "severity": round(max(0.7, score), 3),
                "target": pool,
                "summary": (
                    f"Mempool flow-correlation: {len(group)} same-pool swap(s), "
                    f"max slippage {int(max_slip)}bps, {clustered} high-slippage — "
                    "sandwich/front-run pattern."
                ),
                "evidence": {
                    "pool": pool, "swap_count": len(group),
                    "max_slippage_bps": max_slip, "clustered_high_slippage": clustered,
                    "senders": [d.get("sender") for d in group],
                },
            }
    return worst


def detect_governance_sybil(gov_state: dict[str, Any]) -> dict | None:
    """Relay-family / Sybil clustering analog on governance votes.

    Prefers a real vote distribution (`votes`: list of weights or {voter: weight});
    falls back to the demo `suspicious_votes` counter when that's all there is.
    """
    if not gov_state:
        return None
    votes = gov_state.get("votes")
    weights: list[float] = []
    if isinstance(votes, dict):
        weights = [float(w) for w in votes.values()]
    elif isinstance(votes, list):
        weights = [float(v.get("weight", 1)) if isinstance(v, dict) else float(v) for v in votes]

    if weights:
        g = gini(weights)
        ent = shannon_entropy(weights)
        # High concentration + low entropy = coordinated Sybil bloc.
        score = min(1.0, 0.6 * g + 0.4 * (1 - ent))
        if score < 0.6:
            return None
        return {
            "type": "governance_sybil",
            "severity": round(max(0.7, score), 3),
            "target": "dao-governance",
            "summary": (
                f"Vote-concentration anomaly: Gini={g:.2f}, entropy={ent:.2f} across "
                f"{len(weights)} voters — coordinated voting bloc."
            ),
            "evidence": {"voter_count": len(weights), "gini": round(g, 3),
                         "entropy": round(ent, 3), "top_weight": max(weights)},
        }

    # Demo fallback: only the coarse counter is available.
    suspicious = int(gov_state.get("suspicious_votes", 0) or 0)
    if suspicious > 0:
        return {
            "type": "governance_sybil",
            "severity": 0.85,
            "target": "dao-governance",
            "summary": f"Concentrated voting burst on {gov_state.get('active_proposals', '?')} active proposal(s).",
            "evidence": {"suspicious_votes": suspicious, **gov_state},
        }
    return None


def detect_validator_decentralization(validators: list[dict[str, Any]]) -> dict | None:
    """Onionoo relay-health analog: stake-concentration Gini + Nakamoto coefficient
    + uptime outliers across the validator set."""
    if not validators or len(validators) < 2:
        return None
    stakes = [float(v.get("stake", v.get("delegation_rate", 0)) or 0) for v in validators]
    uptimes = [float(v.get("uptime_pct", 100)) for v in validators]
    g = gini(stakes) if any(stakes) else 0.0
    nak = nakamoto_coefficient(stakes) if any(stakes) else len(validators)
    low_uptime = [v for v, u in zip(validators, uptimes) if u < 95.0]

    # Centralisation risk: few entities control the chain, or validators degrading.
    concentration_risk = g > 0.8 or (0 < nak <= 3)
    if not concentration_risk and not low_uptime:
        return None
    severity = 0.6 + 0.3 * g + (0.1 if low_uptime else 0.0)
    return {
        "type": "validator_centralization",
        "severity": round(min(0.95, severity), 3),
        "target": "validator-set",
        "summary": (
            f"Decentralization health: stake Gini={g:.2f}, Nakamoto={nak}, "
            f"{len(low_uptime)} validator(s) below 95% uptime."
        ),
        "evidence": {"validator_count": len(validators), "stake_gini": round(g, 3),
                     "nakamoto_coefficient": nak, "low_uptime_count": len(low_uptime)},
    }


# ─── engine ────────────────────────────────────────────────────────────────────

# Metrics whose sudden spikes/drops matter, and the direction that is anomalous.
_BASELINE_METRICS = {
    "gas_price_motes": "high",
    "mempool_pending_count": "high",
    "tx_volume_24h": "high",
    "liquidity_depth_usd": "low",
    "slippage_estimate_bps": "high",
    "governance_quorum_pct": "low",
}


class AnomalyEngine:
    """Runs all detectors and keeps rolling baselines across scan cycles."""

    def __init__(self, domain: str = "casper_defi"):
        self.domain = domain
        self.baseline = RollingBaseline()
        self._last_health: dict[str, Any] = {}

    def scan(self, client) -> tuple[list[dict], dict]:
        findings: list[dict] = []

        # 1) Baseline z-score anomalies (OONI-style) on market/pool telemetry.
        market = _safe(client.get_market_snapshot, {})
        pool = _safe(lambda: client.get_pool_info("cspr-usdc"), {})
        metrics = {**market, **{k: pool[k] for k in ("liquidity_depth_usd", "slippage_estimate_bps") if k in pool}}
        for metric, value in metrics.items():
            if metric not in _BASELINE_METRICS or not _is_number(value):
                continue
            self.baseline.update(metric, value)
            z = self.baseline.zscore(metric, value)
            direction = _BASELINE_METRICS[metric]
            anomalous = (z > 3.0 and direction == "high") or (z < -3.0 and direction == "low")
            if anomalous:
                findings.append({
                    "type": "baseline_anomaly",
                    "severity": round(min(0.9, 0.6 + abs(z) * 0.05), 3),
                    "target": metric,
                    "summary": f"{metric} z-score {z:+.1f}σ vs rolling baseline (anomalous {direction}).",
                    "evidence": {"metric": metric, "value": value, "zscore": round(z, 2),
                                 "entropy": round(self.baseline.entropy(metric), 3)},
                })

        # 2) MEV / sandwich (flow-timing correlation).
        mev = detect_mev(_safe(client.get_pending_deploys, []))
        if mev:
            findings.append(mev)

        # 3) Governance Sybil (relay-family clustering).
        gov = _safe(lambda: client.query_contract_state("governance-demo"), {})
        sybil = detect_governance_sybil(gov)
        if sybil:
            findings.append(sybil)

        # 4) Validator decentralization (Onionoo relay-health).
        validators = _collect_validators(client)
        vc = detect_validator_decentralization(validators)
        if vc:
            findings.append(vc)

        self._last_health = self._network_health(validators, market, findings)
        return findings, self._last_health

    def _network_health(self, validators, market, findings) -> dict:
        stakes = [float(v.get("stake", v.get("delegation_rate", 0)) or 0) for v in validators]
        g = gini(stakes) if any(stakes) else 0.0
        nak = nakamoto_coefficient(stakes) if any(stakes) else len(validators)
        crit = sum(1 for f in findings if f["severity"] >= 0.85)
        overall = "critical" if crit else ("elevated" if findings else "nominal")
        return {
            "overall": overall,
            "open_anomalies": len(findings),
            "critical_anomalies": crit,
            "stake_gini": round(g, 3),
            "nakamoto_coefficient": nak,
            "validator_count": len(validators),
            "mempool_zscore": round(self.baseline.zscore("mempool_pending_count",
                                     market.get("mempool_pending_count", 0)), 2),
            "timestamp": time.time(),
        }

    @property
    def last_health(self) -> dict:
        return self._last_health


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _collect_validators(client) -> list[dict]:
    """Prefer a live validator set; fall back to a small synthetic set derived
    from the single-validator demo method so the detector always has data."""
    getter = getattr(client, "get_validators", None)
    if callable(getter):
        vs = _safe(getter, [])
        if vs:
            return vs
    # Demo fallback: build a plausible set around the single demo validator.
    base = _safe(lambda: client.get_validator_info("validator-17"), {})
    up = float(base.get("uptime_pct", 99.2))
    return [
        {"validator": "validator-01", "stake": 3_200_000, "uptime_pct": up},
        {"validator": "validator-02", "stake": 1_100_000, "uptime_pct": 99.0},
        {"validator": "validator-03", "stake": 640_000, "uptime_pct": 98.4},
        {"validator": "validator-17", "stake": 420_000, "uptime_pct": up},
        {"validator": "validator-22", "stake": 210_000, "uptime_pct": 93.1},
    ]


# Module-level singletons keyed by domain (baselines persist across requests).
_ENGINES: dict[str, AnomalyEngine] = {}


def get_engine(domain: str = "casper_defi") -> AnomalyEngine:
    if domain not in _ENGINES:
        _ENGINES[domain] = AnomalyEngine(domain)
    return _ENGINES[domain]
