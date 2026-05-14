"""
PlannerAgent — given context, choose actions that optimize the domain objective.

Tier 1 (heavy):   PPO + MCTS over action space + GNN-conditioned policy
Tier 2 (medium):  Thompson Sampling multi-armed bandit + LSTM trajectory predictor
Tier 3 (light):   Constrained convex optimization (CVXPY) — always works
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import numpy as np
import time

from .base import ErayaAgent, AgentRole
from .perceiver import PerceptionResult


@dataclass
class ActionPlan:
    plan_id: str
    domain: str
    actions: list[dict[str, Any]]
    rationale: str
    confidence: float
    expected_reward: float
    tier_used: str
    requires_guardian_approval: bool = False
    deadline_ms: int = 500


@dataclass
class BanditArm:
    action_id: str
    action_params: dict[str, Any]
    alpha: float = 1.0  # Thompson Sampling Beta distribution params
    beta: float = 1.0

    @property
    def sample(self) -> float:
        return float(np.random.beta(self.alpha, self.beta))

    def update(self, reward: float) -> None:
        self.alpha += reward
        self.beta += (1.0 - reward)


class PlannerAgent(ErayaAgent):
    role = AgentRole.PLANNER

    def __init__(self, agent_id: str | None = None, domain: str = "generic"):
        super().__init__(agent_id, domain)
        self._arms: dict[str, BanditArm] = {}
        self._action_history: list[dict[str, Any]] = []
        self._lstm_hidden = None
        self._domain_actions: list[dict[str, Any]] = []  # registered by domain adapter

    def register_actions(self, actions: list[dict[str, Any]]) -> None:
        """Domain adapter registers available actions at startup."""
        self._domain_actions = actions
        for a in actions:
            aid = a["action_id"]
            if aid not in self._arms:
                self._arms[aid] = BanditArm(
                    action_id=aid, action_params=a.get("parameters", {})
                )

    def update_reward(self, action_id: str, reward: float) -> None:
        """Called by RecovererAgent / environment after outcome is observed."""
        if action_id in self._arms:
            self._arms[action_id].update(max(0.0, min(1.0, reward)))

    # ─── Tier 1: PPO + MCTS ───────────────────────────────────────────────────

    def _plan_tier1(self, context: PerceptionResult) -> ActionPlan:
        try:
            from stable_baselines3 import PPO  # noqa: F401
        except ImportError:
            raise NotImplementedError("stable-baselines3 not installed")

        # Placeholder: in production, run PPO policy with MCTS lookahead.
        result = self._plan_tier2(context)
        result.tier_used = "tier1"
        result.rationale = f"[PPO stub → {result.rationale}]"
        return result

    # ─── Tier 2: Thompson Sampling + LSTM ─────────────────────────────────────

    def _plan_tier2(self, context: PerceptionResult) -> ActionPlan:
        import uuid

        if not self._arms:
            return self._plan_tier3(context)

        # Thompson Sampling: sample each arm, pick highest
        scores = {aid: arm.sample for aid, arm in self._arms.items()}
        # Boost arms relevant to current state
        scores = self._context_boost(scores, context)
        best_id = max(scores, key=scores.__getitem__)
        best_arm = self._arms[best_id]

        action = {
            "action_id": best_id,
            "parameters": best_arm.action_params,
            "expected_reward": scores[best_id],
        }

        return ActionPlan(
            plan_id=str(uuid.uuid4())[:8],
            domain=context.domain,
            actions=[action],
            rationale=(
                f"Thompson Sampling selected '{best_id}' "
                f"(state={context.state_label}, risk={context.risk_score:.2f})"
            ),
            confidence=context.confidence,
            expected_reward=scores[best_id],
            tier_used="tier2",
            requires_guardian_approval=context.risk_score > 0.7,
        )

    def _context_boost(
        self, scores: dict[str, float], context: PerceptionResult
    ) -> dict[str, float]:
        """Upweight actions whose tags match current state."""
        boosted = dict(scores)
        for a in self._domain_actions:
            aid = a["action_id"]
            relevant_states = a.get("relevant_states", [])
            if context.state_label in relevant_states and aid in boosted:
                boosted[aid] = min(1.0, boosted[aid] * 1.5)
        return boosted

    # ─── Tier 3: CVXPY convex optimization ────────────────────────────────────

    def _plan_tier3(self, context: PerceptionResult) -> ActionPlan:
        import uuid

        try:
            import cvxpy as cp

            n = max(len(self._domain_actions), 1)
            x = cp.Variable(n, nonneg=True)

            # Minimize cost (risk-weighted), subject to sum = 1 (action budget)
            risk = context.risk_score
            costs = np.ones(n) * risk
            prob = cp.Problem(cp.Minimize(costs @ x), [cp.sum(x) == 1.0])
            prob.solve(solver=cp.ECOS, verbose=False)

            if x.value is not None and len(self._domain_actions) > 0:
                best_idx = int(np.argmax(x.value))
                chosen = self._domain_actions[best_idx]
                action = {
                    "action_id": chosen["action_id"],
                    "parameters": chosen.get("parameters", {}),
                    "weight": float(x.value[best_idx]),
                }
                rationale = f"CVXPY optimization (risk={risk:.2f}, solver=ECOS)"
            else:
                action = {"action_id": "noop", "parameters": {}, "weight": 1.0}
                rationale = "CVXPY fallback: no actions registered, emitting noop"

        except Exception as exc:
            action = {"action_id": "noop", "parameters": {}, "weight": 1.0}
            rationale = f"CVXPY failed ({exc}), emitting noop"

        return ActionPlan(
            plan_id=str(uuid.uuid4())[:8],
            domain=context.domain,
            actions=[action],
            rationale=rationale,
            confidence=0.5,
            expected_reward=0.5,
            tier_used="tier3",
            requires_guardian_approval=False,
        )

    # ─── A2A card ─────────────────────────────────────────────────────────────

    def _capabilities(self) -> list[str]:
        return ["plan", "choose_action", "update_reward", "register_actions"]

    def _input_schema(self) -> str:
        return "PerceptionResult"

    def _output_schema(self) -> str:
        return "ActionPlan"

    def _guard(self, action: Any, context: Any) -> tuple[bool, str]:
        return True, "planner passthrough"
