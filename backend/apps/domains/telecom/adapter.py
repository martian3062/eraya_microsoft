"""
TelecomEnvironment — 5G self-healing domain adapter.

Actions:
  band_switch      — switch UE to a different frequency band
  slice_realloc    — reallocate network slice resources
  trigger_handoff  — force handoff to neighboring cell
  power_adjust     — adjust cell transmit power
  ntn_failover     — failover to NTN (satellite) link
"""
from __future__ import annotations

import time
import uuid
from typing import Iterator

from apps.domains.base import ErayaEnvironment, RawSignal, DomainAction, ActionOutcome
from .simulator import FiveGSimulator, ScenarioType


class TelecomEnvironment(ErayaEnvironment):
    domain_name = "5g"

    def __init__(self, use_open5gs: bool = False):
        self._sim = FiveGSimulator(n_ues=5, n_cells=3, tick_ms=0)
        self._use_open5gs = use_open5gs
        self._action_log: list[dict] = []

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

        if action.type == "band_switch":
            success = self._band_switch(action.parameters)
        elif action.type == "slice_realloc":
            success = self._slice_realloc(action.parameters)
        elif action.type == "trigger_handoff":
            success = self._trigger_handoff(action.parameters)
        elif action.type == "power_adjust":
            success = self._power_adjust(action.parameters)
        elif action.type == "ntn_failover":
            success = self._ntn_failover(action.parameters)
        elif action.type == "inject_scenario":
            self._sim.inject_scenario(
                ScenarioType(action.parameters.get("scenario", "normal"))
            )
            success = True
        else:
            success = True  # noop

        latency_ms = (time.monotonic() - start) * 1000
        outcome = ActionOutcome(
            action_id=action.action_id,
            success=success,
            reward=0.8 if success else 0.2,
            state_delta={"action_executed": action.type},
            latency_ms=latency_ms,
        )
        self._action_log.append({
            "action": action.type,
            "params": action.parameters,
            "success": success,
            "ts": time.time(),
        })
        return outcome

    def reward(self, outcome: ActionOutcome) -> float:
        return outcome.reward

    def available_actions(self) -> list[dict]:
        return [
            {
                "action_id": "band_switch",
                "type": "band_switch",
                "description": "Switch UE to a different frequency band",
                "parameters": {"target_band": "n78", "ue_id": "ue-001"},
                "relevant_states": ["degraded", "critical"],
            },
            {
                "action_id": "slice_realloc",
                "type": "slice_realloc",
                "description": "Reallocate network slice resources",
                "parameters": {"slice_id": "embb", "prb_ratio": 0.6},
                "relevant_states": ["degraded", "congestion"],
            },
            {
                "action_id": "trigger_handoff",
                "type": "trigger_handoff",
                "description": "Force handoff to neighboring cell",
                "parameters": {"target_cell": "cell-002", "ue_id": "ue-001"},
                "relevant_states": ["critical", "recovering"],
            },
            {
                "action_id": "power_adjust",
                "type": "power_adjust",
                "description": "Adjust cell transmit power",
                "parameters": {"cell_id": "cell-001", "delta_dbm": -3},
                "relevant_states": ["normal", "degraded"],
            },
            {
                "action_id": "ntn_failover",
                "type": "ntn_failover",
                "description": "Failover to NTN (satellite) link",
                "parameters": {"ue_id": "ue-001"},
                "relevant_states": ["critical"],
                "requires_guardian": True,
            },
        ]

    def bootstrap_graph(self) -> list[dict]:
        nodes = []
        for snap in self._sim.snapshot():
            nodes.append({
                "node_id": snap["source"],
                "node_type": "ue",
                "domain": self.domain_name,
                "properties": snap["features"],
            })
        for cell in self._sim._cells:
            nodes.append({
                "node_id": cell.cell_id,
                "node_type": "cell",
                "domain": self.domain_name,
                "properties": {"band": cell.band, "users": cell.current_users},
            })
        return nodes

    def inject_failure(self, scenario: str = "interference") -> None:
        try:
            self._sim.inject_scenario(ScenarioType(scenario))
        except ValueError:
            pass

    # ─── Action implementations ───────────────────────────────────────────────

    def _band_switch(self, params: dict) -> bool:
        return True  # simulator: always succeeds

    def _slice_realloc(self, params: dict) -> bool:
        return True

    def _trigger_handoff(self, params: dict) -> bool:
        ue_id = params.get("ue_id")
        target = params.get("target_cell")
        if not ue_id or not target:
            return False
        for ue in self._sim._ues:
            if ue.ue_id == ue_id:
                ue.attached_cell = target
                return True
        return False

    def _power_adjust(self, params: dict) -> bool:
        return True

    def _ntn_failover(self, params: dict) -> bool:
        # NTN adds latency — simulate
        for ue in self._sim._ues:
            if ue.ue_id == params.get("ue_id"):
                ue.latency_ms += 600  # satellite RTT
        return True

    def health_check(self) -> dict:
        snap = self._sim.snapshot()
        avg_rsrp = sum(s["features"]["rsrp"] for s in snap) / max(len(snap), 1)
        avg_sinr = sum(s["features"]["sinr"] for s in snap) / max(len(snap), 1)
        return {
            "domain": self.domain_name,
            "status": "active",
            "ue_count": len(self._sim._ues),
            "cell_count": len(self._sim._cells),
            "avg_rsrp_dbm": round(avg_rsrp, 1),
            "avg_sinr_db": round(avg_sinr, 1),
            "scenario": self._sim._scenario.value,
        }
