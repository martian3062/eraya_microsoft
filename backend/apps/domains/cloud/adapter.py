"""
CloudEnvironment — cloud cost optimization domain adapter.

Actions: scale replicas, shift spot/reserved mix, adjust HPA thresholds,
         restart OOM pod, drain node.
"""
from __future__ import annotations

import time
from typing import Iterator

from apps.domains.base import ErayaEnvironment, RawSignal, DomainAction, ActionOutcome
from .simulator import CloudSimulator, LoadPattern


class CloudEnvironment(ErayaEnvironment):
    domain_name = "cloud"

    def __init__(self):
        self._sim = CloudSimulator(tick_ms=0)

    def signal_stream(self) -> Iterator[RawSignal]:
        for raw in self._sim.stream():
            yield RawSignal(
                timestamp=raw["timestamp"],
                domain=self.domain_name,
                source=raw["source"],
                features=raw["features"],
                metadata=raw["metadata"],
            )

    def execute_action(self, action: DomainAction) -> ActionOutcome:
        start = time.monotonic()
        success = True

        if action.type == "scale_replicas":
            success = self._sim.scale_service(
                action.parameters["service"], action.parameters["replicas"]
            )
        elif action.type == "shift_spot":
            success = self._shift_spot(action.parameters)
        elif action.type == "restart_pod":
            success = True  # simulator: pod restart always succeeds
        elif action.type == "inject_pattern":
            self._sim.inject_pattern(LoadPattern(action.parameters.get("pattern", "steady")))
        elif action.type == "adjust_hpa":
            success = True

        latency_ms = (time.monotonic() - start) * 1000
        reward = self._compute_reward(action, success)
        return ActionOutcome(
            action_id=action.action_id,
            success=success,
            reward=reward,
            state_delta={"action": action.type, "params": action.parameters},
            latency_ms=latency_ms,
        )

    def reward(self, outcome: ActionOutcome) -> float:
        return outcome.reward

    def _compute_reward(self, action: DomainAction, success: bool) -> float:
        if not success:
            return 0.1
        cost_now = self._sim.total_cost_per_hour()
        # Reward inversely proportional to cost (normalized to ~$5/hr baseline)
        cost_reward = max(0.0, 1.0 - cost_now / 5.0)
        return round(min(1.0, 0.5 + cost_reward * 0.5), 3)

    def _shift_spot(self, params: dict) -> bool:
        service_name = params.get("service")
        new_ratio = params.get("spot_ratio", 0.5)
        for svc in self._sim._services:
            if svc.name == service_name:
                svc.spot_ratio = max(0.0, min(1.0, new_ratio))
                return True
        return False

    def available_actions(self) -> list[dict]:
        return [
            {
                "action_id": "scale_up",
                "type": "scale_replicas",
                "description": "Scale up replicas to handle load",
                "parameters": {"service": "api-gateway", "replicas": 5},
                "relevant_states": ["critical", "degraded"],
            },
            {
                "action_id": "scale_down",
                "type": "scale_replicas",
                "description": "Scale down idle replicas to reduce cost",
                "parameters": {"service": "analytics-batch", "replicas": 2},
                "relevant_states": ["normal"],
            },
            {
                "action_id": "increase_spot",
                "type": "shift_spot",
                "description": "Shift batch workloads to spot instances",
                "parameters": {"service": "recommendation", "spot_ratio": 0.9},
                "relevant_states": ["normal"],
            },
            {
                "action_id": "restart_pod",
                "type": "restart_pod",
                "description": "Restart OOM or stuck pod",
                "parameters": {"service": "payment-svc"},
                "relevant_states": ["critical"],
                "requires_guardian": True,
            },
        ]

    def health_check(self) -> dict:
        return {
            "domain": self.domain_name,
            "status": "active",
            "services": len(self._sim._services),
            "total_cost_per_hour": round(self._sim.total_cost_per_hour(), 3),
            "pattern": self._sim._pattern.value,
        }
