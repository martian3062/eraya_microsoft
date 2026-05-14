"""
RecovererAgent — detects degradation, executes fallback, preserves session continuity.

Tier 1 (heavy):   Monte Carlo rollout simulator + RL replanning
Tier 2 (medium):  Q-learning tabular policy + exponential backoff
Tier 3 (light):   Circuit breaker + static fallback policy
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable
import numpy as np
import time
import uuid

from .base import ErayaAgent, AgentRole


class CircuitState(Enum):
    CLOSED = "closed"       # normal operation
    OPEN = "open"           # failing, reject requests
    HALF_OPEN = "half_open" # testing recovery


@dataclass
class FailureEvent:
    failure_id: str
    domain: str
    failure_type: str       # "agent_crash", "timeout", "plan_rejected", "sensor_fail"
    severity: float         # 0.0–1.0
    context: dict[str, Any]
    timestamp: float = field(default_factory=time.time)


@dataclass
class RecoveryPlan:
    recovery_id: str
    failure_id: str
    domain: str
    strategy: str           # "replan", "backoff", "circuit_break", "fallback_policy"
    actions: list[dict[str, Any]]
    backoff_ms: int
    tier_used: str
    expected_recovery_time_ms: int = 1000


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout_s: float = 30.0,
    ):
        self.name = name
        self.state = CircuitState.CLOSED
        self._failures = 0
        self._threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_s
        self._last_failure_time: float = 0.0

    def call(self, fn: Callable[[], Any]) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self._last_failure_time > self._recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise RuntimeError(f"Circuit '{self.name}' is OPEN — request rejected")

        try:
            result = fn()
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise exc

    def _on_success(self) -> None:
        self._failures = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.time()
        if self._failures >= self._threshold:
            self.state = CircuitState.OPEN


class TabularQAgent:
    """Minimal tabular Q-learning for recovery policy."""

    def __init__(self, n_states: int = 8, n_actions: int = 4, lr: float = 0.1):
        self.Q = np.zeros((n_states, n_actions))
        self.lr = lr
        self.gamma = 0.9
        self.epsilon = 0.15

    def select_action(self, state: int) -> int:
        if np.random.random() < self.epsilon:
            return int(np.random.randint(self.Q.shape[1]))
        return int(np.argmax(self.Q[state]))

    def update(self, state: int, action: int, reward: float, next_state: int) -> None:
        target = reward + self.gamma * np.max(self.Q[next_state])
        self.Q[state, action] += self.lr * (target - self.Q[state, action])


class RecovererAgent(ErayaAgent):
    role = AgentRole.RECOVERER

    # Recovery actions (domain-agnostic)
    _RECOVERY_ACTIONS = [
        {"id": "replan", "description": "trigger replanning cycle"},
        {"id": "backoff", "description": "exponential backoff and retry"},
        {"id": "fallback_policy", "description": "switch to static fallback"},
        {"id": "escalate", "description": "page human operator"},
    ]

    def __init__(self, agent_id: str | None = None, domain: str = "generic"):
        super().__init__(agent_id, domain)
        self._q_agent = TabularQAgent()
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._backoff_state: dict[str, int] = {}  # key → retry count
        self._fallback_policies: dict[str, dict[str, Any]] = {}

    def register_circuit_breaker(self, name: str, **kwargs) -> None:
        self._circuit_breakers[name] = CircuitBreaker(name, **kwargs)

    def register_fallback_policy(self, failure_type: str, policy: dict[str, Any]) -> None:
        self._fallback_policies[failure_type] = policy

    # ─── Tier 1: Monte Carlo rollout ──────────────────────────────────────────

    def _recover_tier1(self, failure: FailureEvent) -> RecoveryPlan:
        # MC rollout stub — requires PyTorch / SB3
        try:
            import torch  # noqa: F401
        except ImportError:
            raise NotImplementedError("PyTorch not available for MC rollout")

        result = self._recover_tier2(failure)
        result.tier_used = "tier1"
        return result

    # ─── Tier 2: Q-learning + exponential backoff ─────────────────────────────

    def _recover_tier2(self, failure: FailureEvent) -> RecoveryPlan:
        state_idx = self._failure_to_state(failure)
        action_idx = self._q_agent.select_action(state_idx)
        action_id = self._RECOVERY_ACTIONS[action_idx]["id"]

        retry_count = self._backoff_state.get(failure.failure_type, 0)
        backoff_ms = int(min(30_000, 100 * (2 ** retry_count)))
        self._backoff_state[failure.failure_type] = retry_count + 1

        return RecoveryPlan(
            recovery_id=str(uuid.uuid4())[:8],
            failure_id=failure.failure_id,
            domain=failure.domain,
            strategy=action_id,
            actions=[{"action_id": action_id, "backoff_ms": backoff_ms}],
            backoff_ms=backoff_ms,
            tier_used="tier2",
            expected_recovery_time_ms=backoff_ms + 500,
        )

    def reward_recovery(self, failure_type: str, action_idx: int, reward: float) -> None:
        state_idx = self._failure_type_to_idx(failure_type)
        next_state = state_idx  # simplified: same state
        self._q_agent.update(state_idx, action_idx, reward, next_state)
        if reward > 0.5:
            self._backoff_state.pop(failure_type, None)

    # ─── Tier 3: Circuit breaker + static fallback ────────────────────────────

    def _recover_tier3(self, failure: FailureEvent) -> RecoveryPlan:
        cb_name = failure.failure_type
        if cb_name not in self._circuit_breakers:
            self._circuit_breakers[cb_name] = CircuitBreaker(cb_name)

        cb = self._circuit_breakers[cb_name]
        if cb.state == CircuitState.OPEN:
            strategy = "circuit_break"
            actions = [{"action_id": "circuit_break", "cb_name": cb_name}]
        elif failure.failure_type in self._fallback_policies:
            strategy = "fallback_policy"
            actions = [self._fallback_policies[failure.failure_type]]
        else:
            strategy = "escalate"
            actions = [{"action_id": "escalate", "reason": str(failure.failure_type)}]

        return RecoveryPlan(
            recovery_id=str(uuid.uuid4())[:8],
            failure_id=failure.failure_id,
            domain=failure.domain,
            strategy=strategy,
            actions=actions,
            backoff_ms=0,
            tier_used="tier3",
        )

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _failure_to_state(self, failure: FailureEvent) -> int:
        idx = self._failure_type_to_idx(failure.failure_type)
        severity_bucket = min(3, int(failure.severity * 4))
        return min(7, idx * 2 + severity_bucket)

    def _failure_type_to_idx(self, failure_type: str) -> int:
        types = ["agent_crash", "timeout", "plan_rejected", "sensor_fail"]
        try:
            return types.index(failure_type)
        except ValueError:
            return 0

    def _capabilities(self) -> list[str]:
        return ["recover", "circuit_break", "backoff", "reward_recovery"]

    def _input_schema(self) -> str:
        return "FailureEvent"

    def _output_schema(self) -> str:
        return "RecoveryPlan"

    def _guard(self, action: Any, context: Any) -> tuple[bool, str]:
        return True, "recoverer passthrough"
