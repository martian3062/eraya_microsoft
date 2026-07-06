"""Proactive KAVACHA scanner for Casper DeFi state."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
import uuid
from typing import Any

from core.a2a.bus import A2ABus, get_bus
from core.a2a.schemas import A2AMessage
from core.casper.mcp import CasperMCPClient


@dataclass
class Threat:
    threat_id: str
    type: str
    severity: float
    target: str
    summary: str
    status: str = "open"
    timestamp: float = field(default_factory=time.time)
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["severity_label"] = "critical" if self.severity >= 0.85 else "high" if self.severity >= 0.7 else "medium"
        return data


class ThreatScanner:
    """Monitors mempool, liquidity, and governance signals before execution."""

    def __init__(
        self,
        client: CasperMCPClient | None = None,
        bus: A2ABus | None = None,
        watched_pools: list[dict[str, str]] | None = None,
        publish_events: bool = True,
    ):
        self.client = client or CasperMCPClient()
        self.bus = bus or get_bus()
        self.publish_events = publish_events
        self.watched_pools = watched_pools or [
            {"id": "cspr-usdc", "address": "hash-cspr-usdc-demo"},
            {"id": "cspr-weth", "address": "hash-cspr-weth-demo"},
        ]

    def scan_cycle(self) -> list[Threat]:
        # Statistical anomaly intelligence (Tor-technique lineage): rolling
        # baselines/z-scores, MEV flow-correlation, governance Sybil clustering
        # and validator decentralization. See core/casper/anomaly.py.
        from core.casper.anomaly import get_engine

        findings, health = get_engine("casper_defi").scan(self.client)
        self._last_health = health

        threats: list[Threat] = [
            Threat(
                threat_id=str(uuid.uuid4())[:8],
                type=f["type"],
                severity=float(f["severity"]),
                target=f["target"],
                summary=f["summary"],
                evidence=f.get("evidence", {}),
            )
            for f in findings
        ]

        # Complement: legacy liquidity-drain snapshot check across watched pools.
        for pool in self.watched_pools:
            state = self.client.query_contract_state(pool["address"])
            last = float(state.get("last_liquidity", 0) or 1)
            current = float(state.get("liquidity", 0))
            drop = 1.0 - (current / last)
            if drop > 0.25:
                threats.append(Threat(
                    threat_id=str(uuid.uuid4())[:8],
                    type="liquidity_drain",
                    severity=0.8 if drop < 0.5 else 0.92,
                    target=pool["id"],
                    summary=f"Liquidity dropped {drop:.0%} versus last snapshot.",
                    evidence={**state, "drop_pct": round(drop, 3)},
                ))

        for threat in threats:
            self._publish(threat)
        return threats

    def network_health(self) -> dict[str, Any]:
        """Latest network-health summary from the anomaly engine (Gini, Nakamoto,
        open/critical anomaly counts). Populated by the most recent scan_cycle()."""
        health = getattr(self, "_last_health", None)
        if health:
            return health
        from core.casper.anomaly import get_engine
        _, health = get_engine("casper_defi").scan(self.client)
        self._last_health = health
        return health

    @staticmethod
    def _is_sandwich_risk(deploy: dict[str, Any]) -> bool:
        return deploy.get("type") == "swap" and float(deploy.get("max_slippage_bps", 0)) > 100

    def _publish(self, threat: Threat) -> None:
        if not self.publish_events:
            return
        try:
            self.bus.publish(A2AMessage(
                from_agent="threat-scanner",
                to_agent="guardian",
                message_type="threat.detected",
                domain="casper_defi",
                payload=threat.to_dict(),
            ))
        except Exception:
            pass
