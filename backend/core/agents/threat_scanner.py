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
        threats: list[Threat] = []
        for deploy in self.client.get_pending_deploys():
            if self._is_sandwich_risk(deploy):
                threats.append(Threat(
                    threat_id=str(uuid.uuid4())[:8],
                    type="sandwich_attack",
                    severity=0.9,
                    target=deploy["pool"],
                    summary="High-slippage swap in mempool could front-run treasury execution.",
                    evidence=deploy,
                ))

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

        governance_state = self.client.query_contract_state("governance-demo")
        if governance_state.get("suspicious_votes", 0) > 0:
            threats.append(Threat(
                threat_id=str(uuid.uuid4())[:8],
                type="governance_attack",
                severity=0.85,
                target="dao-governance",
                summary="Concentrated voting burst detected on active proposals.",
                evidence=governance_state,
            ))

        for threat in threats:
            self._publish(threat)
        return threats

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
