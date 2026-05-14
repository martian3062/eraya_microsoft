"""
5G signal simulator — generates realistic RAN telemetry for demo.

Produces: RSRP, SINR, CQI, throughput, latency, packet loss, handoff risk.
Supports: normal operation, gradual degradation, sudden failure injection.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class ScenarioType(Enum):
    NORMAL = "normal"
    HIGHWAY_HANDOFF = "highway_handoff"
    INDOOR_ATTENUATION = "indoor_attenuation"
    CONGESTION = "congestion"
    INTERFERENCE = "interference"
    NTN_TRANSITION = "ntn_transition"  # terrestrial → satellite


@dataclass
class Cell:
    cell_id: str
    band: str       # "n78", "n41", "n28", "n77"
    technology: str # "NR", "LTE"
    latitude: float
    longitude: float
    max_users: int = 200
    current_users: int = field(default_factory=lambda: random.randint(20, 150))


@dataclass
class UEState:
    ue_id: str
    velocity_kmh: float = 0.0
    environment: str = "outdoor"   # outdoor | indoor | vehicular
    attached_cell: str = "cell-001"
    rsrp: float = -80.0            # dBm, range: -140 to -44
    sinr: float = 15.0             # dB, range: -20 to 30
    cqi: int = 10                  # 0–15
    throughput_mbps: float = 50.0
    latency_ms: float = 20.0
    packet_loss_pct: float = 0.1


class FiveGSimulator:
    """Infinite signal stream — plug into TelecomEnvironment.signal_stream()."""

    def __init__(self, n_ues: int = 5, n_cells: int = 3, tick_ms: int = 500):
        self.tick_ms = tick_ms
        self._cells = self._init_cells(n_cells)
        self._ues = self._init_ues(n_ues)
        self._scenario = ScenarioType.NORMAL
        self._step = 0

    def _init_cells(self, n: int) -> list[Cell]:
        bands = ["n78", "n41", "n28"]
        return [
            Cell(
                cell_id=f"cell-{i+1:03d}",
                band=bands[i % len(bands)],
                technology="NR",
                latitude=28.6 + i * 0.01,
                longitude=77.2 + i * 0.01,
            )
            for i in range(n)
        ]

    def _init_ues(self, n: int) -> list[UEState]:
        return [
            UEState(
                ue_id=f"ue-{i+1:03d}",
                velocity_kmh=random.uniform(0, 120),
                environment=random.choice(["outdoor", "indoor", "vehicular"]),
                attached_cell=self._cells[i % len(self._cells)].cell_id,
            )
            for i in range(n)
        ]

    def inject_scenario(self, scenario: ScenarioType) -> None:
        self._scenario = scenario

    def stream(self) -> Iterator[dict]:
        while True:
            self._step += 1
            for ue in self._ues:
                self._evolve_ue(ue)
                yield self._ue_to_signal(ue)
            if self.tick_ms > 0:
                time.sleep(self.tick_ms / 1000)

    def snapshot(self) -> list[dict]:
        """One reading per UE — for REST API demo."""
        snapshots = []
        for ue in self._ues:
            self._evolve_ue(ue)
            snapshots.append(self._ue_to_signal(ue))
        return snapshots

    def _evolve_ue(self, ue: UEState) -> None:
        noise = lambda s=2.0: random.gauss(0, s)
        t = self._step

        if self._scenario == ScenarioType.NORMAL:
            ue.rsrp = max(-140, min(-44, ue.rsrp + noise(1.0)))
            ue.sinr = max(-20, min(30, ue.sinr + noise(0.5)))
            ue.latency_ms = max(5, ue.latency_ms + noise(1.0))
            ue.packet_loss_pct = max(0, min(10, ue.packet_loss_pct + noise(0.05)))

        elif self._scenario == ScenarioType.HIGHWAY_HANDOFF:
            # Oscillating RSRP simulating cell boundary crossing
            ue.rsrp = -90 + 20 * math.sin(t / 10) + noise(3)
            ue.sinr = 5 + 10 * math.sin(t / 10) + noise(1)
            ue.velocity_kmh = 90 + noise(5)
            ue.latency_ms = 30 + 20 * abs(math.sin(t / 10))

        elif self._scenario == ScenarioType.INDOOR_ATTENUATION:
            ue.rsrp = max(-130, ue.rsrp - 0.5)
            ue.sinr = max(-10, ue.sinr - 0.3)
            ue.cqi = max(0, ue.cqi - 1 if t % 10 == 0 else ue.cqi)

        elif self._scenario == ScenarioType.CONGESTION:
            cell = next((c for c in self._cells if c.cell_id == ue.attached_cell), None)
            if cell:
                cell.current_users = min(cell.max_users, cell.current_users + 2)
                load = cell.current_users / cell.max_users
                ue.throughput_mbps = max(1, 100 * (1 - load) + noise(2))
                ue.latency_ms = 20 + 200 * load + noise(5)

        elif self._scenario == ScenarioType.INTERFERENCE:
            ue.sinr = max(-20, ue.sinr - 5 + noise(2))
            ue.packet_loss_pct = min(50, ue.packet_loss_pct + 2)

        # Derive CQI from SINR
        ue.cqi = max(0, min(15, int((ue.sinr + 20) / (50 / 15))))
        ue.throughput_mbps = max(0.1, ue.cqi * 8.0 + noise(2))

    def _ue_to_signal(self, ue: UEState) -> dict:
        return {
            "timestamp": time.time(),
            "source": ue.ue_id,
            "features": {
                "rsrp": round(ue.rsrp, 2),
                "sinr": round(ue.sinr, 2),
                "cqi": float(ue.cqi),
                "throughput_mbps": round(ue.throughput_mbps, 2),
                "latency_ms": round(ue.latency_ms, 2),
                "packet_loss_pct": round(ue.packet_loss_pct, 3),
                "velocity_kmh": round(ue.velocity_kmh, 1),
            },
            "metadata": {
                "attached_cell": ue.attached_cell,
                "environment": ue.environment,
                "scenario": self._scenario.value,
            },
        }
