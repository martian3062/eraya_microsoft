"""Local/on-chain reputation ledger facade for Casper agents."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import time
from typing import Any


@dataclass
class ReputationRecord:
    agent_id: str
    action_id: str
    success: bool
    reward: float
    timestamp: float
    tx_hash: str | None = None


class ReputationTracker:
    """Tracks EMA trust locally and batches records for chain anchoring."""

    def __init__(self, flush_interval: int = 10):
        self.flush_interval = flush_interval
        self.ema_scores: dict[str, float] = {}
        self.success_counts: dict[str, int] = {}
        self.slash_totals: dict[str, int] = {}
        self.pending_records: list[ReputationRecord] = []
        self.ledger: list[ReputationRecord] = []

    def record_outcome(self, agent_id: str, action_id: str, success: bool, reward: float) -> ReputationRecord:
        reward = max(0.0, min(1.0, reward))
        current = self.ema_scores.get(agent_id, 0.75)
        self.ema_scores[agent_id] = 0.9 * current + 0.1 * reward
        if success:
            self.success_counts[agent_id] = self.success_counts.get(agent_id, 0) + 1
        record = ReputationRecord(agent_id, action_id, success, reward, time.time())
        self.pending_records.append(record)
        self.ledger.append(record)
        if len(self.pending_records) >= self.flush_interval:
            self.flush_to_chain()
        return record

    def get_trust_score(self, agent_id: str) -> float:
        return round(self.ema_scores.get(agent_id, 0.75) * 1000, 2)

    def slash(self, agent_id: str, reason: str, amount_motes: int) -> dict[str, Any]:
        self.slash_totals[agent_id] = self.slash_totals.get(agent_id, 0) + amount_motes
        self.record_outcome(agent_id, f"slash:{reason}", False, 0.0)
        return {"agent_id": agent_id, "reason": reason, "amount_motes": amount_motes}

    def flush_to_chain(self) -> str:
        payload = "|".join(f"{r.agent_id}:{r.action_id}:{r.reward:.3f}" for r in self.pending_records)
        tx_hash = "deploy-reputation-" + hashlib.sha256(payload.encode()).hexdigest()[:18]
        for record in self.pending_records:
            record.tx_hash = tx_hash
        self.pending_records = []
        return tx_hash

    def snapshot(self) -> dict[str, Any]:
        agents = []
        for agent_id in sorted(self.ema_scores):
            agents.append({
                "agent_id": agent_id,
                "role": agent_id.split("-")[0],
                "score": self.get_trust_score(agent_id),
                "ema_reward": round(self.ema_scores[agent_id], 3),
                "successful_actions": self.success_counts.get(agent_id, 0),
                "slashed_motes": self.slash_totals.get(agent_id, 0),
                "trend": "up" if self.ema_scores[agent_id] >= 0.76 else "watch",
            })
        anchor = self.ledger[-1].tx_hash if self.ledger and self.ledger[-1].tx_hash else None
        return {
            "agents": agents,
            "on_chain_anchor": anchor or "pending-demo-batch",
            "recent_records": [asdict(r) for r in self.ledger[-10:]],
        }


_tracker: ReputationTracker | None = None


def get_reputation_tracker() -> ReputationTracker:
    global _tracker
    if _tracker is None:
        _tracker = ReputationTracker(flush_interval=4)
        _seed_demo(_tracker)
    return _tracker


def _seed_demo(tracker: ReputationTracker) -> None:
    samples = [
        ("perceiver-casper-001", "signal-quality", True, 0.84),
        ("planner-casper-001", "rebalance-plan", True, 0.81),
        ("recoverer-casper-001", "rollback-ready", True, 0.78),
        ("guardian-casper-001", "r005-veto", True, 0.92),
        ("planner-casper-001", "oversize-swap", False, 0.42),
        ("guardian-casper-001", "r008-quarantine", True, 0.88),
        ("perceiver-casper-001", "mempool-depth", True, 0.79),
        ("recoverer-casper-001", "retry-deploy", True, 0.74),
    ]
    for agent_id, action_id, success, reward in samples:
        tracker.record_outcome(agent_id, action_id, success, reward)
