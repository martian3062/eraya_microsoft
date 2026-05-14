"""
ErayaEnvironment — domain adapter contract.

To add a new domain to the swarm, subclass ErayaEnvironment and
implement these 3 methods. The 4 agents and all protocols remain unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Iterator
import time
import uuid


@dataclass
class RawSignal:
    timestamp: float = field(default_factory=time.time)
    domain: str = "generic"
    source: str = "unknown"
    features: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DomainAction:
    action_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = "noop"
    parameters: dict[str, Any] = field(default_factory=dict)
    requires_guardian: bool = False
    domain: str = "generic"


@dataclass
class ActionOutcome:
    action_id: str
    success: bool
    reward: float           # 0.0–1.0
    state_delta: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


class ErayaEnvironment(ABC):
    """
    Write 3 methods → plug any domain into Eraya.
    Same 4 agents, same A2A protocol, same Guardian.
    """

    domain_name: str = "generic"

    @abstractmethod
    def signal_stream(self) -> Iterator[RawSignal]:
        """Yields real-time signals. Can be infinite (streaming) or finite (batch)."""

    @abstractmethod
    def execute_action(self, action: DomainAction) -> ActionOutcome:
        """Execute an action, return outcome including reward signal."""

    @abstractmethod
    def reward(self, outcome: ActionOutcome) -> float:
        """Compute scalar reward for RL update. Range: 0.0–1.0."""

    def available_actions(self) -> list[dict[str, Any]]:
        """Return list of action specs for PlannerAgent.register_actions()."""
        return []

    def bootstrap_graph(self) -> list[dict[str, Any]]:
        """Seed the ErayaGraph with domain entities. Returns node dicts."""
        return []

    def health_check(self) -> dict[str, Any]:
        return {"domain": self.domain_name, "status": "ok"}


class ErayaSchema(ABC):
    """Optional: declare typed Pydantic schemas for domain I/O."""
    context_class: type
    action_class: type
    outcome_class: type
