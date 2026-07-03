"""
PerceiverAgent — converts raw environment signals into structured context.

Tier 1 (heavy):   Transformer encoder + GNN topology mapper
Tier 2 (medium):  Kalman filter + XGBoost classifier + HMM state tracker
Tier 3 (light):   Bayesian classifier + rule-based feature extraction
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from .base import ErayaAgent, AgentRole


@dataclass
class RawSignal:
    timestamp: float
    domain: str
    source: str
    features: dict[str, float]
    metadata: dict[str, Any] | None = None


@dataclass
class PerceptionResult:
    timestamp: float
    domain: str
    state_label: str            # human-readable state ("handoff_risk", "sepsis_rising", "oom_imminent")
    confidence: float           # 0.0–1.0
    risk_score: float           # 0.0–1.0
    features: dict[str, float]  # smoothed/extracted features
    tier_used: str
    topology: dict[str, Any] | None = None  # GNN output (tier 1 only)


class PerceiverAgent(ErayaAgent):
    role = AgentRole.PERCEIVER

    def __init__(self, agent_id: str | None = None, domain: str = "generic"):
        super().__init__(agent_id, domain)
        self._kalman: dict[str, Any] = {}   # per-feature Kalman filters
        self._hmm = None
        self._xgb_model = None
        self._feature_history: list[np.ndarray] = []
        self._state_labels: list[str] = ["normal", "degraded", "critical", "recovering"]
        self._initialized = False
        self._tabpfn = None   # lazy TabPFN 3 refiner (core/providers/risk.py)

    # ─── Tier 1: Transformer + GNN ────────────────────────────────────────────

    def _perceive_tier1(self, signal: RawSignal) -> PerceptionResult:
        try:
            import torch  # noqa: F401
        except ImportError:
            raise NotImplementedError("PyTorch not installed — tier 1 unavailable")

        # Placeholder: in production, run the signal through a domain-specific
        # Transformer encoder and a GNN over the topology graph.
        # For now, delegates to tier 2 with GNN topology stub.
        result = self._perceive_tier2(signal)
        result.tier_used = "tier1"
        result.topology = {"nodes": [], "edges": [], "note": "GNN stub — install PyG"}
        return result

    # ─── Tier 2: Kalman + XGBoost + HMM ──────────────────────────────────────

    def _perceive_tier2(self, signal: RawSignal) -> PerceptionResult:
        features_raw = np.array(list(signal.features.values()), dtype=float)

        # Kalman smoothing per feature
        smoothed = self._kalman_smooth(signal.features)
        features_smooth = np.array(list(smoothed.values()), dtype=float)

        # Track state history for HMM
        self._feature_history.append(features_smooth)
        if len(self._feature_history) > 100:
            self._feature_history.pop(0)

        # XGBoost classification
        state_label, confidence = self._xgb_classify(features_smooth)

        # HMM state refinement if enough history
        if len(self._feature_history) >= 5:
            state_label, confidence = self._hmm_refine(
                state_label, confidence, features_smooth
            )

        # TabPFN 3 tabular-foundation-model refinement (core/providers/risk.py).
        # No-op until enough labelled history AND tabpfn is available; otherwise
        # the XGBoost/HMM result stands unchanged.
        state_label, confidence = self._tabpfn_refine(
            state_label, confidence, features_smooth
        )

        risk_score = self._compute_risk(features_smooth, state_label)

        return PerceptionResult(
            timestamp=signal.timestamp,
            domain=signal.domain,
            state_label=state_label,
            confidence=confidence,
            risk_score=risk_score,
            features=smoothed,
            tier_used="tier2",
        )

    def _kalman_smooth(self, features: dict[str, float]) -> dict[str, float]:
        try:
            from filterpy.kalman import KalmanFilter
        except ImportError:
            return features  # fall through without smoothing

        smoothed = {}
        for key, value in features.items():
            if key not in self._kalman:
                kf = KalmanFilter(dim_x=2, dim_z=1)
                kf.F = np.array([[1., 1.], [0., 1.]])   # state transition
                kf.H = np.array([[1., 0.]])              # measurement
                kf.R = np.array([[5.]])                  # measurement noise
                kf.Q = np.eye(2) * 0.1                   # process noise
                kf.x = np.array([[value], [0.]])
                kf.P = np.eye(2) * 100
                self._kalman[key] = kf
            kf = self._kalman[key]
            kf.predict()
            kf.update(np.array([[value]]))
            smoothed[key] = float(kf.x[0])
        return smoothed

    def _xgb_classify(self, features: np.ndarray) -> tuple[str, float]:
        if self._xgb_model is None or len(self._feature_history) < 10:
            # Before model is trained, use rule-based classification
            return self._rule_classify(features)
        try:
            proba = self._xgb_model.predict_proba(features.reshape(1, -1))[0]
            idx = int(np.argmax(proba))
            return self._state_labels[idx % len(self._state_labels)], float(proba[idx])
        except Exception:
            return self._rule_classify(features)

    def _hmm_refine(
        self, state_label: str, confidence: float, features: np.ndarray
    ) -> tuple[str, float]:
        try:
            from hmmlearn import hmm
        except ImportError:
            return state_label, confidence

        if self._hmm is None and len(self._feature_history) >= 20:
            obs = np.array(self._feature_history[-20:])
            self._hmm = hmm.GaussianHMM(
                n_components=len(self._state_labels), covariance_type="diag", n_iter=20
            )
            try:
                self._hmm.fit(obs)
            except Exception:
                self._hmm = None
                return state_label, confidence

        if self._hmm is None:
            return state_label, confidence

        try:
            obs_seq = np.array(self._feature_history[-10:])
            _, state_seq = self._hmm.decode(obs_seq)
            hmm_state = self._state_labels[state_seq[-1] % len(self._state_labels)]
            # Blend XGBoost + HMM
            if hmm_state == state_label:
                confidence = min(1.0, confidence + 0.1)
            else:
                confidence = max(0.0, confidence - 0.1)
                state_label = hmm_state if confidence < 0.5 else state_label
        except Exception:
            pass
        return state_label, confidence

    def _tabpfn_refine(
        self, state_label: str, confidence: float, features: np.ndarray
    ) -> tuple[str, float]:
        """Refine (state_label, confidence) with TabPFN 3 when available.

        Feeds the current (smoothed features -> current label) into a rolling
        in-context buffer, then asks TabPFN for its own prediction. Fully
        graceful: returns the inputs unchanged if the refiner or its deps are
        absent, or if there isn't enough labelled history yet.
        """
        try:
            if self._tabpfn is None:
                from core.providers.risk import TabPFNRefiner
                self._tabpfn = TabPFNRefiner()
            label_idx = (
                self._state_labels.index(state_label)
                if state_label in self._state_labels else 0
            )
            self._tabpfn.observe(features, label_idx)
            pred = self._tabpfn.predict(features)
            if pred is not None:
                idx, conf = pred
                new_label = self._state_labels[idx % len(self._state_labels)]
                # Blend: agreement boosts confidence; disagreement only flips
                # the label when TabPFN is clearly more certain.
                if new_label == state_label:
                    confidence = min(1.0, max(confidence, conf) + 0.05)
                elif conf > confidence:
                    state_label, confidence = new_label, conf
        except Exception:
            pass
        return state_label, confidence

    # ─── Tier 3: Rule-based Bayesian ──────────────────────────────────────────

    def _perceive_tier3(self, signal: RawSignal) -> PerceptionResult:
        features = signal.features
        state_label, confidence = self._rule_classify(
            np.array(list(features.values()), dtype=float)
        )
        risk_score = self._compute_risk(
            np.array(list(features.values()), dtype=float), state_label
        )
        return PerceptionResult(
            timestamp=signal.timestamp,
            domain=signal.domain,
            state_label=state_label,
            confidence=confidence,
            risk_score=risk_score,
            features=features,
            tier_used="tier3",
        )

    # ─── Shared helpers ───────────────────────────────────────────────────────

    def _rule_classify(self, features: np.ndarray) -> tuple[str, float]:
        if len(features) == 0:
            return "normal", 0.5
        mean_val = float(np.mean(features))
        std_val = float(np.std(features))
        anomaly_score = std_val / (abs(mean_val) + 1e-6)
        if anomaly_score > 2.0:
            return "critical", 0.75
        if anomaly_score > 1.0:
            return "degraded", 0.65
        if anomaly_score > 0.5:
            return "recovering", 0.6
        return "normal", 0.85

    def _compute_risk(self, features: np.ndarray, state: str) -> float:
        base = {"normal": 0.1, "recovering": 0.35, "degraded": 0.65, "critical": 0.9}
        return base.get(state, 0.5)

    # ─── A2A card ─────────────────────────────────────────────────────────────

    def _capabilities(self) -> list[str]:
        return ["perceive", "classify_state", "smooth_signals", "compute_risk"]

    def _input_schema(self) -> str:
        return "RawSignal"

    def _output_schema(self) -> str:
        return "PerceptionResult"

    def _guard(self, action: Any, context: Any) -> tuple[bool, str]:
        # Perceiver doesn't take actions — always approve (passthrough)
        return True, "perceiver has no actions to guard"
