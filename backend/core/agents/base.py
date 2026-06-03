"""
ErayaAgent — base class for all Eraya agent archetypes.

The 4-method contract: perceive, plan, recover, guard.
The 3-tier cascade runs automatically based on environment context.
Every agent has a defined fallback path — unlike every other agentic framework.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from enum import Enum
import time
import uuid
import logging

from core.telemetry import agent_span


class AgentTier(Enum):
    HEAVY = 1   # GPU + full ML stack, >100ms latency budget
    MEDIUM = 2  # CPU + XGBoost/Kalman/HMM, >30ms budget
    LIGHT = 3   # CVXPY + rules, always works


class AgentRole(Enum):
    PERCEIVER = "perceiver"
    PLANNER = "planner"
    RECOVERER = "recoverer"
    GUARDIAN = "guardian"


class AgentStatus(Enum):
    IDLE = "idle"
    ACTIVE = "active"
    DEGRADED = "degraded"
    QUARANTINED = "quarantined"


@dataclass
class EnvironmentContext:
    has_gpu: bool = False
    latency_budget_ms: int = 500
    available_memory_mb: int = 1024
    signal_quality: float = 1.0     # 0.0–1.0; below 0.5 forces lighter tier
    domain: str = "generic"


@dataclass
class AgentCard:
    """A2A capability declaration — published at agent startup for peer discovery."""
    agent_id: str
    name: str
    role: AgentRole
    version: str
    capabilities: list[str]
    input_schema: str
    output_schema: str
    latency_sla_ms: int
    trust_tier: str         # "high" | "medium" | "low"
    current_tier: AgentTier
    status: AgentStatus
    domain: str


@dataclass
class AgentMetrics:
    total_calls: int = 0
    tier1_calls: int = 0
    tier2_calls: int = 0
    tier3_calls: int = 0
    total_latency_ms: float = 0.0
    errors: int = 0
    guardian_vetoes: int = 0
    last_active: float = field(default_factory=time.time)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.total_calls, 1)


class ErayaAgent(ABC):
    """
    Abstract base for all Eraya archetypes.

    Subclasses implement _perceive_tier{1,2,3}, _plan_tier{1,2,3},
    _recover_tier{1,2,3}, and _guard. The cascade engine handles tier
    selection and automatic fallback — subclasses never call each other's tiers.
    """

    role: AgentRole  # declared on each subclass

    def __init__(self, agent_id: str | None = None, domain: str = "generic"):
        self.agent_id = agent_id or f"{self.role.value}-{uuid.uuid4().hex[:8]}"
        self.domain = domain
        self.status = AgentStatus.IDLE
        self.metrics = AgentMetrics()
        self._env_ctx = EnvironmentContext(domain=domain)
        self._logger = logging.getLogger(f"eraya.{self.role.value}.{self.agent_id[:12]}")

    # ─── Abstract tier methods ─────────────────────────────────────────────────

    def _perceive_tier1(self, signal: Any) -> Any:
        raise NotImplementedError

    def _perceive_tier2(self, signal: Any) -> Any:
        raise NotImplementedError

    def _perceive_tier3(self, signal: Any) -> Any:
        raise NotImplementedError

    def _plan_tier1(self, context: Any) -> Any:
        raise NotImplementedError

    def _plan_tier2(self, context: Any) -> Any:
        raise NotImplementedError

    def _plan_tier3(self, context: Any) -> Any:
        raise NotImplementedError

    def _recover_tier1(self, failure: Any) -> Any:
        raise NotImplementedError

    def _recover_tier2(self, failure: Any) -> Any:
        raise NotImplementedError

    def _recover_tier3(self, failure: Any) -> Any:
        raise NotImplementedError

    @abstractmethod
    def _guard(self, action: Any, context: Any) -> tuple[bool, str]:
        """Returns (approved, reason). Guardian veto logic — always required."""

    # ─── Public API ────────────────────────────────────────────────────────────

    def perceive(self, signal: Any) -> Any:
        return self._cascade("perceive", signal)

    def plan(self, context: Any) -> Any:
        return self._cascade("plan", context)

    def recover(self, failure: Any) -> Any:
        return self._cascade("recover", failure)

    def guard(self, action: Any, context: Any) -> tuple[bool, str]:
        start = time.monotonic()
        try:
            result = self._guard(action, context)
            self._record_call(start, AgentTier.LIGHT)  # guardian tier doesn't degrade
            return result
        except Exception as exc:
            self._logger.error("Guardian error: %s", exc)
            self.metrics.errors += 1
            return False, f"Guardian internal error: {exc}"

    # ─── Cascade engine ────────────────────────────────────────────────────────

    def _cascade(self, method: str, input_data: Any) -> Any:
        preferred = self._select_tier()
        tier_order = _tier_fallback_chain(preferred)
        self.status = AgentStatus.ACTIVE
        self.metrics.total_calls += 1
        start = time.monotonic()

        for tier in tier_order:
            fn_name = f"_{method}_tier{tier.value}"   # → _plan_tier1 / tier2 / tier3
            fn = getattr(self, fn_name, None)
            if fn is None:
                continue
            try:
                span_attrs = {
                    "agent.id": self.agent_id,
                    "agent.domain": self.domain,
                    "tier": tier.name,
                    "fallback": str(tier != preferred),
                }
                with agent_span(f"eraya.{self.role.value}.{method}.{tier.name.lower()}", span_attrs):
                    result = fn(input_data)
                self._record_call(start, tier)
                if tier != preferred:
                    self._logger.warning(
                        "%s fell back from %s to %s", method, preferred.name, tier.name
                    )
                return result
            except NotImplementedError:
                continue
            except Exception as exc:
                self._logger.warning("%s tier %s failed: %s", method, tier.name, exc)

        self.status = AgentStatus.DEGRADED
        self.metrics.errors += 1
        raise RuntimeError(f"{self.agent_id}: all {method} tiers exhausted")

    def _select_tier(self) -> AgentTier:
        ctx = self._env_ctx
        if ctx.has_gpu and ctx.latency_budget_ms > 100 and ctx.signal_quality > 0.7:
            return AgentTier.HEAVY
        if ctx.latency_budget_ms > 30 and ctx.signal_quality > 0.3:
            return AgentTier.MEDIUM
        return AgentTier.LIGHT

    def _record_call(self, start: float, tier: AgentTier) -> None:
        ms = (time.monotonic() - start) * 1000
        self.metrics.total_latency_ms += ms
        self.metrics.last_active = time.time()
        counter = f"tier{tier.value}_calls"
        setattr(self.metrics, counter, getattr(self.metrics, counter) + 1)
        self.status = AgentStatus.IDLE

    # ─── Environment + A2A ────────────────────────────────────────────────────

    def update_environment(self, ctx: EnvironmentContext) -> None:
        self._env_ctx = ctx

    def get_agent_card(self) -> AgentCard:
        return AgentCard(
            agent_id=self.agent_id,
            name=self.__class__.__name__,
            role=self.role,
            version="0.1.0",
            capabilities=self._capabilities(),
            input_schema=self._input_schema(),
            output_schema=self._output_schema(),
            latency_sla_ms=self._env_ctx.latency_budget_ms,
            trust_tier="high",
            current_tier=self._select_tier(),
            status=self.status,
            domain=self.domain,
        )

    def health_check(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "domain": self.domain,
            "status": self.status.value,
            "current_tier": self._select_tier().name,
            "metrics": {
                "total_calls": self.metrics.total_calls,
                "avg_latency_ms": round(self.metrics.avg_latency_ms, 2),
                "tier1_calls": self.metrics.tier1_calls,
                "tier2_calls": self.metrics.tier2_calls,
                "tier3_calls": self.metrics.tier3_calls,
                "errors": self.metrics.errors,
            },
        }

    def _capabilities(self) -> list[str]:
        return [self.role.value]

    def _input_schema(self) -> str:
        return "Any"

    def _output_schema(self) -> str:
        return "Any"


def _tier_fallback_chain(preferred: AgentTier) -> list[AgentTier]:
    """Returns tiers in fallback order starting from preferred."""
    all_tiers = [AgentTier.HEAVY, AgentTier.MEDIUM, AgentTier.LIGHT]
    idx = all_tiers.index(preferred)
    return all_tiers[idx:]
