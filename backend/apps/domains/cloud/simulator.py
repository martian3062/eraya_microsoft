"""
Cloud cost simulator — generates Kubernetes workload metrics for demo.

Produces: CPU/memory utilization, request rate, error rate, cost/hour,
          replica counts, spot vs reserved mix.
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterator


class LoadPattern(Enum):
    STEADY = "steady"
    RAMP_UP = "ramp_up"
    SPIKE = "spike"
    MEMORY_LEAK = "memory_leak"
    COST_SPIKE = "cost_spike"


@dataclass
class Service:
    name: str
    replicas: int
    cpu_request: float      # cores per replica
    memory_request_gb: float
    spot_ratio: float       # 0.0 = all reserved, 1.0 = all spot
    cost_per_hour: float
    max_replicas: int = 20
    min_replicas: int = 1

    # Runtime state
    cpu_util: float = 0.3
    mem_util: float = 0.4
    rps: float = 100.0
    error_rate: float = 0.001
    p99_latency_ms: float = 50.0


class CloudSimulator:
    SERVICES = [
        Service("api-gateway",     replicas=3, cpu_request=0.5, memory_request_gb=1.0, spot_ratio=0.0, cost_per_hour=0.15),
        Service("payment-svc",     replicas=2, cpu_request=1.0, memory_request_gb=2.0, spot_ratio=0.0, cost_per_hour=0.25),
        Service("user-svc",        replicas=3, cpu_request=0.5, memory_request_gb=1.0, spot_ratio=0.5, cost_per_hour=0.10),
        Service("recommendation",  replicas=5, cpu_request=2.0, memory_request_gb=4.0, spot_ratio=0.8, cost_per_hour=0.80),
        Service("analytics-batch", replicas=8, cpu_request=4.0, memory_request_gb=8.0, spot_ratio=0.9, cost_per_hour=1.60),
    ]

    def __init__(self, tick_ms: int = 0):
        self.tick_ms = tick_ms
        self._services = [Service(**s.__dict__) for s in self.SERVICES]  # deep copy
        self._pattern = LoadPattern.STEADY
        self._step = 0
        self._total_cost = 0.0

    def inject_pattern(self, pattern: LoadPattern) -> None:
        self._pattern = pattern

    def stream(self) -> Iterator[dict]:
        while True:
            self._step += 1
            for svc in self._services:
                self._evolve_service(svc)
                yield self._svc_to_signal(svc)
            if self.tick_ms > 0:
                time.sleep(self.tick_ms / 1000)

    def snapshot(self) -> list[dict]:
        snapshots = []
        for svc in self._services:
            self._evolve_service(svc)
            snapshots.append(self._svc_to_signal(svc))
        return snapshots

    def total_cost_per_hour(self) -> float:
        return sum(
            svc.cost_per_hour * svc.replicas * (1 - svc.spot_ratio * 0.7)
            for svc in self._services
        )

    def scale_service(self, name: str, replicas: int) -> bool:
        for svc in self._services:
            if svc.name == name:
                svc.replicas = max(svc.min_replicas, min(svc.max_replicas, replicas))
                return True
        return False

    def _evolve_service(self, svc: Service) -> None:
        noise = lambda s=0.02: random.gauss(0, s)
        t = self._step

        if self._pattern == LoadPattern.STEADY:
            svc.cpu_util = max(0.05, min(0.95, svc.cpu_util + noise()))
            svc.mem_util = max(0.05, min(0.95, svc.mem_util + noise(0.01)))
            svc.rps = max(1, svc.rps + random.gauss(0, 5))
            svc.error_rate = max(0, min(0.1, svc.error_rate + noise(0.0005)))

        elif self._pattern == LoadPattern.SPIKE:
            spike = max(0, math.sin(t / 20) ** 2)
            svc.cpu_util = min(0.99, 0.3 + 0.65 * spike + noise())
            svc.rps = 100 + 500 * spike + random.gauss(0, 10)
            svc.p99_latency_ms = 50 + 500 * spike + noise(10)

        elif self._pattern == LoadPattern.MEMORY_LEAK:
            leak_rate = 0.002 if svc.name == "payment-svc" else 0.0
            svc.mem_util = min(0.99, svc.mem_util + leak_rate + noise(0.001))
            svc.p99_latency_ms = 50 + 1000 * max(0, svc.mem_util - 0.8)

        elif self._pattern == LoadPattern.RAMP_UP:
            ramp = min(1.0, t / 200)
            svc.cpu_util = min(0.95, 0.1 + 0.85 * ramp + noise())
            svc.rps = 10 + 990 * ramp + noise(20)

        elif self._pattern == LoadPattern.COST_SPIKE:
            svc.replicas = min(svc.max_replicas, svc.replicas + (1 if t % 30 == 0 else 0))

        svc.cpu_util = round(max(0.01, min(0.99, svc.cpu_util)), 3)
        svc.mem_util = round(max(0.01, min(0.99, svc.mem_util)), 3)

    def _svc_to_signal(self, svc: Service) -> dict:
        cost_per_hour = svc.cost_per_hour * svc.replicas * (1 - svc.spot_ratio * 0.7)
        return {
            "timestamp": time.time(),
            "source": svc.name,
            "features": {
                "cpu_util": svc.cpu_util,
                "mem_util": svc.mem_util,
                "replicas": float(svc.replicas),
                "rps": round(svc.rps, 1),
                "error_rate": round(svc.error_rate, 4),
                "p99_latency_ms": round(svc.p99_latency_ms, 1),
                "cost_per_hour": round(cost_per_hour, 3),
                "spot_ratio": svc.spot_ratio,
            },
            "metadata": {
                "service": svc.name,
                "pattern": self._pattern.value,
                "max_replicas": svc.max_replicas,
            },
        }
