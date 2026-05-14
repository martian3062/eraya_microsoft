"""
ICUEnvironment — ICU patient monitoring domain adapter.

Actions are clinical recommendations — GuardianAgent enforces
confidence > 0.8 before any suggestion is surfaced to operator.
"""
from __future__ import annotations

import time
from typing import Iterator

from apps.domains.base import ErayaEnvironment, RawSignal, DomainAction, ActionOutcome
from .simulator import ICUSimulator, ClinicalScenario


class ICUEnvironment(ErayaEnvironment):
    domain_name = "icu"

    def __init__(self):
        self._sim = ICUSimulator(n_patients=3, tick_ms=0)
        self._intervention_log: list[dict] = []

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

        # All ICU actions require guardian_approved flag
        if not action.parameters.get("guardian_approved", False):
            return ActionOutcome(
                action_id=action.action_id,
                success=False,
                reward=0.0,
                error="ICU action requires guardian approval",
                latency_ms=0.0,
            )

        success = True
        if action.type == "recommend_vasopressor":
            success = self._log_recommendation(action, "vasopressor")
        elif action.type == "recommend_fluid_bolus":
            success = self._log_recommendation(action, "fluid_bolus")
        elif action.type == "escalate_to_physician":
            success = self._log_recommendation(action, "physician_escalation")
        elif action.type == "switch_manual_protocol":
            success = self._log_recommendation(action, "manual_fallback")
        elif action.type == "inject_scenario":
            pt_id = action.parameters.get("patient_id", "pt-001")
            scenario = ClinicalScenario(action.parameters.get("scenario", "stable"))
            success = self._sim.inject_scenario(pt_id, scenario)

        latency_ms = (time.monotonic() - start) * 1000
        reward = 0.8 if success else 0.2
        return ActionOutcome(
            action_id=action.action_id,
            success=success,
            reward=reward,
            latency_ms=latency_ms,
        )

    def reward(self, outcome: ActionOutcome) -> float:
        return outcome.reward

    def _log_recommendation(self, action: DomainAction, rec_type: str) -> bool:
        self._intervention_log.append({
            "type": rec_type,
            "patient": action.parameters.get("patient_id"),
            "params": action.parameters,
            "ts": time.time(),
        })
        return True

    def available_actions(self) -> list[dict]:
        return [
            {
                "action_id": "recommend_vasopressor",
                "type": "recommend_vasopressor",
                "description": "Recommend vasopressor titration for hypotension",
                "parameters": {"patient_id": "pt-001", "guardian_approved": False},
                "relevant_states": ["critical", "degraded"],
                "requires_guardian": True,
            },
            {
                "action_id": "recommend_fluid",
                "type": "recommend_fluid_bolus",
                "description": "Recommend 500mL fluid bolus for volume resuscitation",
                "parameters": {"patient_id": "pt-001", "volume_ml": 500, "guardian_approved": False},
                "relevant_states": ["degraded"],
                "requires_guardian": True,
            },
            {
                "action_id": "escalate",
                "type": "escalate_to_physician",
                "description": "Page attending physician for immediate review",
                "parameters": {"patient_id": "pt-001", "guardian_approved": False},
                "relevant_states": ["critical"],
                "requires_guardian": True,
            },
            {
                "action_id": "manual_fallback",
                "type": "switch_manual_protocol",
                "description": "Fall back to manual nursing protocol when model confidence low",
                "parameters": {"patient_id": "pt-001", "guardian_approved": False},
                "relevant_states": ["normal", "recovering"],
            },
        ]

    def health_check(self) -> dict:
        snap = self._sim.snapshot()
        avg_sepsis = sum(s["features"]["sepsis_risk"] for s in snap) / max(len(snap), 1)
        critical = sum(1 for s in snap if s["features"]["sepsis_risk"] > 0.6)
        return {
            "domain": self.domain_name,
            "status": "active",
            "patient_count": len(self._sim._patients),
            "avg_sepsis_risk": round(avg_sepsis, 3),
            "critical_patients": critical,
        }
