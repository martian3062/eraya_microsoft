"""
ICU patient vitals simulator — MIMIC-IV-style synthetic stream.

Vitals: HR, SpO2, SBP, DBP, RR, Temp, Lactate, WBC, Urine output.
Scenarios: stable, post-op recovery, early sepsis, septic shock, respiratory failure.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class ClinicalScenario(Enum):
    STABLE = "stable"
    POST_OP = "post_op"
    EARLY_SEPSIS = "early_sepsis"
    SEPTIC_SHOCK = "septic_shock"
    RESP_FAILURE = "resp_failure"
    RECOVERY = "recovery"


# SOFA score approximation from vitals
def estimate_sofa(vitals: dict) -> float:
    score = 0.0
    if vitals.get("spo2", 100) < 90:
        score += 2
    if vitals.get("sbp", 120) < 70:
        score += 3
    if vitals.get("lactate", 1.0) > 4.0:
        score += 3
    elif vitals.get("lactate", 1.0) > 2.0:
        score += 1
    if vitals.get("urine_ml_hr", 50) < 20:
        score += 2
    return min(24.0, score)


@dataclass
class Patient:
    patient_id: str
    age: int
    weight_kg: float
    scenario: ClinicalScenario = ClinicalScenario.STABLE

    # Vitals (current values)
    hr: float = 72.0         # bpm
    spo2: float = 98.0       # %
    sbp: float = 120.0       # mmHg
    dbp: float = 75.0        # mmHg
    rr: float = 14.0         # breaths/min
    temp_c: float = 37.0     # °C
    lactate: float = 1.0     # mmol/L
    wbc: float = 8.0         # x10^9/L
    urine_ml_hr: float = 60.0

    # Derived
    sofa_score: float = 0.0
    sepsis_risk: float = 0.0


class ICUSimulator:
    def __init__(self, n_patients: int = 3, tick_ms: int = 0):
        self.tick_ms = tick_ms
        self._patients = self._init_patients(n_patients)
        self._step = 0

    def _init_patients(self, n: int) -> list[Patient]:
        scenarios = list(ClinicalScenario)
        return [
            Patient(
                patient_id=f"pt-{i+1:03d}",
                age=random.randint(45, 85),
                weight_kg=random.uniform(55, 100),
                scenario=scenarios[i % len(scenarios)],
            )
            for i in range(n)
        ]

    def inject_scenario(self, patient_id: str, scenario: ClinicalScenario) -> bool:
        for pt in self._patients:
            if pt.patient_id == patient_id:
                pt.scenario = scenario
                return True
        return False

    def stream(self) -> Iterator[dict]:
        while True:
            self._step += 1
            for pt in self._patients:
                self._evolve_patient(pt)
                yield self._patient_to_signal(pt)
            if self.tick_ms > 0:
                time.sleep(self.tick_ms / 1000)

    def snapshot(self) -> list[dict]:
        for pt in self._patients:
            self._evolve_patient(pt)
        return [self._patient_to_signal(pt) for pt in self._patients]

    def _evolve_patient(self, pt: Patient) -> None:
        n = lambda mu=0.0, s=1.0: random.gauss(mu, s)

        if pt.scenario == ClinicalScenario.STABLE:
            pt.hr = max(50, min(100, pt.hr + n(0, 1)))
            pt.spo2 = max(95, min(100, pt.spo2 + n(0, 0.2)))
            pt.sbp = max(100, min(140, pt.sbp + n(0, 1)))
            pt.lactate = max(0.5, min(2.0, pt.lactate + n(0, 0.05)))
            pt.urine_ml_hr = max(40, min(100, pt.urine_ml_hr + n(0, 3)))

        elif pt.scenario == ClinicalScenario.EARLY_SEPSIS:
            # Rising HR, falling BP, rising temp, rising lactate
            pt.hr = min(130, pt.hr + n(0.5, 1))
            pt.sbp = max(85, pt.sbp + n(-0.3, 1))
            pt.temp_c = min(40.0, pt.temp_c + n(0.05, 0.1))
            pt.lactate = min(6.0, pt.lactate + n(0.05, 0.05))
            pt.wbc = min(25.0, pt.wbc + n(0.1, 0.2))
            pt.spo2 = max(88, pt.spo2 + n(-0.1, 0.2))
            pt.urine_ml_hr = max(15, pt.urine_ml_hr + n(-1, 2))

        elif pt.scenario == ClinicalScenario.SEPTIC_SHOCK:
            pt.hr = min(150, pt.hr + n(0.3, 2))
            pt.sbp = max(60, pt.sbp + n(-0.5, 2))
            pt.dbp = max(40, pt.dbp + n(-0.3, 1))
            pt.lactate = min(12.0, pt.lactate + n(0.1, 0.1))
            pt.spo2 = max(80, pt.spo2 + n(-0.2, 0.3))
            pt.urine_ml_hr = max(5, pt.urine_ml_hr + n(-2, 2))

        elif pt.scenario == ClinicalScenario.RESP_FAILURE:
            pt.rr = min(35, pt.rr + n(0.2, 0.5))
            pt.spo2 = max(78, pt.spo2 + n(-0.3, 0.4))
            pt.hr = min(130, pt.hr + n(0.2, 1))

        elif pt.scenario == ClinicalScenario.POST_OP:
            # Gradual normalisation
            pt.hr = max(65, pt.hr + n(-0.1, 1))
            pt.sbp = max(110, min(130, pt.sbp + n(0.1, 1)))
            pt.spo2 = min(99, pt.spo2 + n(0.05, 0.1))

        elif pt.scenario == ClinicalScenario.RECOVERY:
            pt.hr = max(60, min(90, pt.hr + n(-0.2, 0.5)))
            pt.spo2 = min(100, pt.spo2 + n(0.1, 0.1))
            pt.lactate = max(0.8, pt.lactate + n(-0.05, 0.03))

        # Derived scores
        vitals = {
            "spo2": pt.spo2, "sbp": pt.sbp,
            "lactate": pt.lactate, "urine_ml_hr": pt.urine_ml_hr,
        }
        pt.sofa_score = estimate_sofa(vitals)
        pt.sepsis_risk = min(1.0, pt.sofa_score / 12.0)

    def _patient_to_signal(self, pt: Patient) -> dict:
        return {
            "timestamp": time.time(),
            "source": pt.patient_id,
            "features": {
                "hr": round(pt.hr, 1),
                "spo2": round(pt.spo2, 1),
                "sbp": round(pt.sbp, 1),
                "dbp": round(pt.dbp, 1),
                "rr": round(pt.rr, 1),
                "temp_c": round(pt.temp_c, 2),
                "lactate": round(pt.lactate, 2),
                "wbc": round(pt.wbc, 1),
                "urine_ml_hr": round(pt.urine_ml_hr, 1),
                "sofa_score": round(pt.sofa_score, 1),
                "sepsis_risk": round(pt.sepsis_risk, 3),
            },
            "metadata": {
                "patient_id": pt.patient_id,
                "age": pt.age,
                "scenario": pt.scenario.value,
            },
        }
