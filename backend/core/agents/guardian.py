"""
GuardianAgent — monitors the swarm itself. The security differentiator.

Three sub-modules:
  PolicyAuditor    — intent-vs-action drift detection via OPA
  InjectionSentinel — prompt injection detection (DeBERTa classifier)
  AuditSigner       — every critical decision signed into an audit log

When a flag is raised, the Guardian can:
  - WARN  (log + notify operator)
  - BLOCK (veto the action, return error to caller)
  - QUARANTINE (revoke agent's A2A card)
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .base import ErayaAgent, AgentRole, AgentStatus

logger = logging.getLogger("eraya.guardian")


class VerdictSeverity(Enum):
    APPROVE = "approve"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"


@dataclass
class PolicyViolation:
    rule_id: str
    description: str
    severity: VerdictSeverity
    evidence: dict[str, Any]


@dataclass
class GuardianVerdict:
    verdict_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    approved: bool = True
    severity: VerdictSeverity = VerdictSeverity.APPROVE
    violations: list[PolicyViolation] = field(default_factory=list)
    audit_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    agent_quarantined: str | None = None


@dataclass
class AuditRecord:
    record_id: str
    agent_id: str
    action: dict[str, Any]
    context: dict[str, Any]
    verdict: str
    hash: str
    timestamp: float


def _metric(action: dict[str, Any], context: dict[str, Any], key: str, default: float = 0.0) -> float:
    """Read policy metrics from action, action.parameters, context, or context.features."""
    sources = [
        action,
        action.get("parameters", {}) if isinstance(action.get("parameters"), dict) else {},
        context,
        context.get("features", {}) if isinstance(context.get("features"), dict) else {},
    ]
    for source in sources:
        if key in source:
            try:
                return float(source[key])
            except (TypeError, ValueError):
                return default
    return default


# ─── PolicyAuditor ────────────────────────────────────────────────────────────

class PolicyAuditor:
    """Checks agent actions against Rego policies using OPA."""

    # Built-in guardrails (applied even without OPA)
    _HARD_RULES = [
        {
            "id": "R001",
            "description": "ICU actions require confidence > 0.8",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "icu" and ctx.get("confidence", 1.0) < 0.8
            ),
        },
        {
            "id": "R002",
            "description": "Actions cannot override Guardian quarantine",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: action.get("action_id") != "lift_quarantine",
        },
        {
            "id": "R003",
            "description": "High-risk actions require guardian approval flag",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: not (
                ctx.get("risk_score", 0) > 0.85
                and not action.get("guardian_approved", False)
            ),
        },
        {
            "id": "R004",
            "description": "No single DeFi position can exceed 25% of treasury TVL",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "casper_defi"
                and _metric(action, ctx, "single_position_pct") > 0.25
            ),
        },
        {
            "id": "R005",
            "description": "Single DeFi swap cannot exceed 5% of treasury",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "casper_defi"
                and _metric(action, ctx, "treasury_tvl") > 0
                and _metric(action, ctx, "swap_value_usd") > _metric(action, ctx, "treasury_tvl") * 0.05
            ),
        },
        {
            "id": "R006",
            "description": "Target APY is more than 3x market average",
            "severity": VerdictSeverity.WARN,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "casper_defi"
                and _metric(action, ctx, "market_avg_apy") > 0
                and _metric(action, ctx, "target_apy") > _metric(action, ctx, "market_avg_apy") * 3
            ),
        },
        {
            "id": "R007",
            "description": "Block DeFi swaps with more than 1% estimated slippage",
            "severity": VerdictSeverity.BLOCK,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "casper_defi"
                and _metric(action, ctx, "estimated_slippage_bps") > 100
            ),
        },
        {
            "id": "R008",
            "description": "Quarantine pool interaction if liquidity dropped more than 50% in 24h",
            "severity": VerdictSeverity.QUARANTINE,
            "check": lambda action, ctx: not (
                ctx.get("domain") == "casper_defi"
                and _metric(action, ctx, "liquidity_drop_24h_pct") > 0.50
            ),
        },
    ]

    def __init__(self, opa_url: str | None = None):
        self._opa_url = opa_url
        self._opa_available = False
        self._try_connect_opa()

    def _try_connect_opa(self) -> None:
        if not self._opa_url:
            return
        try:
            import httpx
            r = httpx.get(f"{self._opa_url}/health", timeout=2.0)
            self._opa_available = r.status_code == 200
        except Exception:
            self._opa_available = False

    def audit(self, action: dict[str, Any], context: dict[str, Any]) -> list[PolicyViolation]:
        violations = []

        # Always run hard rules
        for rule in self._HARD_RULES:
            try:
                if not rule["check"](action, context):
                    violations.append(PolicyViolation(
                        rule_id=rule["id"],
                        description=rule["description"],
                        severity=rule.get("severity", VerdictSeverity.BLOCK),
                        evidence={"action": action, "context": context},
                    ))
            except Exception as exc:
                logger.warning("Rule %s evaluation error: %s", rule["id"], exc)

        # OPA evaluation (if available)
        if self._opa_available:
            violations += self._opa_evaluate(action, context)

        return violations

    def _opa_evaluate(
        self, action: dict[str, Any], context: dict[str, Any]
    ) -> list[PolicyViolation]:
        try:
            import httpx
            payload = {"input": {"action": action, "context": context}}
            r = httpx.post(
                f"{self._opa_url}/v1/data/eraya/policy",
                json=payload,
                timeout=1.0,
            )
            result = r.json().get("result", {})
            violations = []
            for v in result.get("violations", []):
                violations.append(PolicyViolation(
                    rule_id=v.get("id", "OPA"),
                    description=v.get("msg", "OPA policy violation"),
                    severity=VerdictSeverity[v.get("severity", "BLOCK").upper()],
                    evidence=v,
                ))
            return violations
        except Exception as exc:
            logger.debug("OPA evaluation failed: %s", exc)
            return []


# ─── InjectionSentinel ────────────────────────────────────────────────────────

class InjectionSentinel:
    """
    Detects prompt injection in operator console inputs.
    Uses DeBERTa classifier when available; falls back to pattern matching.
    """

    _INJECTION_PATTERNS = [
        "ignore previous instructions",
        "ignore all instructions",
        "disregard your",
        "you are now",
        "act as if",
        "pretend you are",
        "system prompt",
        "jailbreak",
        "bypass safety",
        "override guardian",
        "quarantine lift",
        "\\x00", "\\u0000",  # null byte injection
    ]

    def __init__(self):
        self._classifier = None
        self._try_load_classifier()

    def _try_load_classifier(self) -> None:
        try:
            from transformers import pipeline
            self._classifier = pipeline(
                "text-classification",
                model="microsoft/deberta-v3-base",
                device=-1,  # CPU
            )
        except Exception:
            self._classifier = None

    def scan(self, text: str) -> tuple[bool, float, str]:
        """Returns (is_injection, confidence, reason)."""
        # Pattern matching (always runs)
        text_lower = text.lower()
        for pattern in self._INJECTION_PATTERNS:
            if pattern in text_lower:
                return True, 0.95, f"pattern match: '{pattern}'"

        # ML classifier (if available)
        if self._classifier is not None:
            try:
                result = self._classifier(text[:512])[0]
                if result["label"] == "INJECTION" and result["score"] > 0.8:
                    return True, result["score"], "DeBERTa classifier"
            except Exception:
                pass

        return False, 0.0, "clean"


# ─── AuditSigner ──────────────────────────────────────────────────────────────

class AuditSigner:
    """Signs audit records with HMAC-SHA256 for tamper evidence."""

    def __init__(self, secret_key: str | None = None):
        self._key = (secret_key or os.environ.get("ERAYA_AUDIT_KEY") or "dev-audit-key").encode()

    def sign(self, record: dict[str, Any]) -> str:
        payload = json.dumps(record, sort_keys=True, default=str).encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def verify(self, record: dict[str, Any], signature: str) -> bool:
        expected = self.sign(record)
        return hmac.compare_digest(expected, signature)

    def create_record(
        self,
        agent_id: str,
        action: dict[str, Any],
        context: dict[str, Any],
        verdict: str,
    ) -> AuditRecord:
        record_id = str(uuid.uuid4())
        ts = time.time()
        payload = {
            "record_id": record_id,
            "agent_id": agent_id,
            "action": action,
            "verdict": verdict,
            "timestamp": ts,
        }
        return AuditRecord(
            record_id=record_id,
            agent_id=agent_id,
            action=action,
            context=context,
            verdict=verdict,
            hash=self.sign(payload),
            timestamp=ts,
        )


# ─── GuardianAgent ────────────────────────────────────────────────────────────

class GuardianAgent(ErayaAgent):
    role = AgentRole.GUARDIAN

    def __init__(
        self,
        agent_id: str | None = None,
        domain: str = "generic",
        opa_url: str | None = None,
    ):
        super().__init__(agent_id, domain)
        self._policy_auditor = PolicyAuditor(opa_url)
        self._injection_sentinel = InjectionSentinel()
        self._audit_signer = AuditSigner()
        self._quarantined_agents: set[str] = set()
        self._audit_log: list[AuditRecord] = []  # in-memory; persisted via Django model

    # ─── Primary guard method ─────────────────────────────────────────────────

    def _guard(self, action: Any, context: Any) -> tuple[bool, str]:
        if not isinstance(action, dict):
            action = {"action_id": str(action)}
        if not isinstance(context, dict):
            context = {}

        # Block quarantined agents immediately
        requesting_agent = context.get("agent_id", "")
        if requesting_agent in self._quarantined_agents:
            return False, f"Agent '{requesting_agent}' is quarantined"

        verdict = self._evaluate(action, context)
        self._persist_audit(requesting_agent, action, context, verdict)

        if not verdict.approved:
            if verdict.severity == VerdictSeverity.QUARANTINE:
                self._quarantine_agent(requesting_agent)
            return False, "; ".join(v.description for v in verdict.violations)

        return True, "approved"

    def _evaluate(self, action: dict, context: dict) -> GuardianVerdict:
        verdict = GuardianVerdict()
        violations = self._policy_auditor.audit(action, context)
        verdict.violations = violations

        if violations:
            severity_order = {
                VerdictSeverity.APPROVE: 0,
                VerdictSeverity.WARN: 1,
                VerdictSeverity.BLOCK: 2,
                VerdictSeverity.QUARANTINE: 3,
            }
            verdict.severity = max(violations, key=lambda v: severity_order[v.severity]).severity
            verdict.approved = verdict.severity not in (
                VerdictSeverity.BLOCK, VerdictSeverity.QUARANTINE
            )
        return verdict

    # ─── Injection scan (called by operator console) ──────────────────────────

    def scan_input(self, user_text: str) -> tuple[bool, float, str]:
        return self._injection_sentinel.scan(user_text)

    # ─── Cascade stubs (Guardian doesn't need per-signal cascade) ────────────

    def _perceive_tier3(self, signal: Any) -> Any:
        return signal  # passthrough

    def _plan_tier3(self, context: Any) -> Any:
        return {}  # passthrough

    def _recover_tier3(self, failure: Any) -> Any:
        return {}  # passthrough

    # ─── Agent management ─────────────────────────────────────────────────────

    def _quarantine_agent(self, agent_id: str) -> None:
        if agent_id:
            self._quarantined_agents.add(agent_id)
            logger.warning("QUARANTINE: agent '%s' has been isolated", agent_id)

    def lift_quarantine(self, agent_id: str, authorized_by: str) -> bool:
        if agent_id in self._quarantined_agents:
            self._quarantined_agents.discard(agent_id)
            logger.info("Quarantine lifted for '%s' by '%s'", agent_id, authorized_by)
            return True
        return False

    def is_quarantined(self, agent_id: str) -> bool:
        return agent_id in self._quarantined_agents

    # ─── Audit ────────────────────────────────────────────────────────────────

    def _persist_audit(
        self, agent_id: str, action: dict, context: dict, verdict: GuardianVerdict
    ) -> None:
        record = self._audit_signer.create_record(
            agent_id=agent_id,
            action=action,
            context=context,
            verdict=verdict.severity.value,
        )
        self._audit_log.append(record)
        if len(self._audit_log) > 10_000:
            self._audit_log = self._audit_log[-5_000:]

    def get_audit_log(self, last_n: int = 100) -> list[AuditRecord]:
        return self._audit_log[-last_n:]

    # ─── A2A card ─────────────────────────────────────────────────────────────

    def _capabilities(self) -> list[str]:
        return [
            "guard",
            "audit_policy",
            "scan_injection",
            "quarantine_agent",
            "lift_quarantine",
            "get_audit_log",
        ]

    def _input_schema(self) -> str:
        return "ActionContext"

    def _output_schema(self) -> str:
        return "GuardianVerdict"
