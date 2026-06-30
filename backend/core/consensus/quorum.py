"""Swarm quorum protocol for high-stakes Casper DeFi actions."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import time
import uuid
from typing import Any, Literal

from core.a2a.bus import A2ABus, get_bus
from core.a2a.schemas import A2AMessage


VoteValue = Literal["approve", "reject", "abstain"]


@dataclass
class Vote:
    agent_id: str
    role: str
    vote: VoteValue
    rationale: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class Proposal:
    proposal_id: str
    proposer: str
    action: dict[str, Any]
    context: dict[str, Any]
    votes: dict[str, Vote] = field(default_factory=dict)
    status: str = "voting"
    threshold: float = 0.6
    created_at: float = field(default_factory=time.time)
    deadline: float = field(default_factory=lambda: time.time() + 30)

    def approval_ratio(self) -> float:
        counted = [v for v in self.votes.values() if v.vote != "abstain"]
        if not counted:
            return 0.0
        return sum(1 for v in counted if v.vote == "approve") / len(counted)

    def rejection_reasons(self) -> list[str]:
        return [v.rationale for v in self.votes.values() if v.vote == "reject"]

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["approval_ratio"] = round(self.approval_ratio(), 3)
        data["required_votes"] = 3
        data["quorum_votes"] = len(self.votes)
        data["votes"] = [asdict(v) for v in self.votes.values()]
        return data


class SwarmQuorum:
    """Voting layer that sits above PlannerAgent for high-stakes execution."""

    def __init__(self, threshold: float = 0.6, bus: A2ABus | None = None, publish_events: bool = True):
        self.threshold = threshold
        self.bus = bus or get_bus()
        self.publish_events = publish_events
        self.active_proposals: dict[str, Proposal] = {}

    def propose(self, proposer: str, action: dict[str, Any], context: dict[str, Any]) -> Proposal:
        proposal = Proposal(
            proposal_id=str(uuid.uuid4())[:8],
            proposer=proposer,
            action=action,
            context=context,
            threshold=self.threshold,
        )
        self.active_proposals[proposal.proposal_id] = proposal
        self._publish("consensus.propose", "swarm", proposal.to_dict())
        return proposal

    def cast_vote(
        self,
        proposal_id: str,
        agent_id: str,
        role: str,
        vote: VoteValue,
        rationale: str,
    ) -> Proposal:
        proposal = self.active_proposals[proposal_id]
        proposal.votes[agent_id] = Vote(agent_id=agent_id, role=role, vote=vote, rationale=rationale)
        self._publish("consensus.vote", proposal.proposer, proposal.to_dict())
        if self._quorum_reached(proposal):
            proposal.status = "approved" if self._majority_approves(proposal) else "rejected"
            self._publish("consensus.result", proposal.proposer, proposal.to_dict())
        return proposal

    @staticmethod
    def should_require_quorum(action: dict[str, Any]) -> bool:
        risk = float(action.get("risk_score", 0.0))
        value_usd = float(action.get("value_usd", 0.0))
        return risk > 0.7 or value_usd > 10_000

    @staticmethod
    def _quorum_reached(proposal: Proposal) -> bool:
        return len(proposal.votes) >= 3

    def _majority_approves(self, proposal: Proposal) -> bool:
        return proposal.approval_ratio() >= self.threshold

    def _publish(self, message_type: str, to_agent: str, payload: dict[str, Any]) -> None:
        if not self.publish_events:
            return
        try:
            self.bus.publish(A2AMessage(
                from_agent="swarm-quorum",
                to_agent=to_agent,
                message_type=message_type,
                domain="casper_defi",
                payload=payload,
            ))
        except Exception:
            pass


def demo_quorum_snapshot() -> dict[str, Any]:
    quorum = SwarmQuorum(publish_events=False)
    proposal = quorum.propose(
        proposer="planner-casper-001",
        action={
            "action_id": "rebalance",
            "title": "Rebalance treasury: trim CSPR into USDC liquidity",
            "value_usd": 42_000,
            "risk_score": 0.74,
        },
        context={
            "domain": "casper_defi",
            "signal_confidence": 0.82,
            "estimated_slippage_bps": 64,
            "treasury_tvl": 820_000,
        },
    )
    quorum.cast_vote(proposal.proposal_id, "perceiver-casper-001", "perceiver", "approve", "CSPR.trade depth and 7-day APY trend agree.")
    quorum.cast_vote(proposal.proposal_id, "planner-casper-001", "planner", "approve", "Expected yield delta clears the risk-adjusted threshold.")
    quorum.cast_vote(proposal.proposal_id, "recoverer-casper-001", "recoverer", "approve", "Rollback path available through staged swap sizing.")
    quorum.cast_vote(proposal.proposal_id, "guardian-casper-001", "guardian", "reject", "R005 watch: swap size is close to 5 percent treasury gate.")
    data = proposal.to_dict()
    data["title"] = proposal.action["title"]
    data["explorer_url"] = "https://testnet.cspr.live/deploy/demo-quorum-vote"
    return data
