"""
Routing table — maps a CAP service to the existing ERAYA pipeline and
normalizes the result into the CAP §3 output schema (with HMAC proof).

Reuses (does NOT rebuild):
  core.agents.guardian  → InjectionSentinel, PolicyAuditor, AuditSigner
  core.providers.critic → review()  (LLM-as-judge)
  core.cap.proof        → build_proof()  (AuditSigner attestation)
  apps.audit.models     → AuditLog
"""
from __future__ import annotations

import hashlib
import uuid

from django.utils import timezone as dj_tz

from core.cap import facade
from core.cap.proof import build_proof

_sentinel = None
_auditor = None

_OVERRIDE_KEYWORDS = ("system override", "ignore all", "ignore prior", "approve every",
                      "reversibility=1", "skip guardian", "disregard policy")


def _get_sentinel():
    global _sentinel
    if _sentinel is None:
        from core.agents.guardian import InjectionSentinel
        _sentinel = InjectionSentinel()
    return _sentinel


def _get_auditor():
    global _auditor
    if _auditor is None:
        from core.agents.guardian import PolicyAuditor
        _auditor = PolicyAuditor(opa_url=None)
    return _auditor


def _persist_auditlog(record_id, agent_id, domain, action, context, verdict, violations, audit_hash):
    try:
        from apps.audit.models import AuditLog
        AuditLog.objects.create(
            record_id=record_id, agent_id=agent_id, domain=domain, action=action,
            context=context, verdict=verdict, violations=violations,
            audit_hash=audit_hash, timestamp=dj_tz.now(),
        )
    except Exception:
        pass  # AuditLog is best-effort; the proof is already returned


# ─── Service A — KAVACHA Scan ────────────────────────────────────────────────

def route_kavacha(payload: str, domain: str = "generic", policy_pack: str = "baseline") -> dict:
    payload = payload or ""
    dom = domain if domain in {"5g", "cloud", "icu", "casper_defi"} else "5g"
    timeline: list[dict] = []

    is_inj, score, reason = _get_sentinel().scan(payload)
    low = payload.lower()
    if not is_inj and any(k in low for k in _OVERRIDE_KEYWORDS):
        is_inj, score, reason = True, max(score, 0.72), "heuristic: override/reversibility keyword"
    timeline.append({"step": "detected", "ok": True, "score": round(score, 4),
                     "detail": f"injection={is_inj} · {reason}"})

    action = {"action_id": "external_delivery",
              "reversibility": 1.0 if is_inj else 0.3, "guardian_approved": False}
    ctx = {"domain": dom, "risk_score": 0.95 if is_inj else 0.4, "confidence": 0.9,
           "agent_id": "cap-requester", "_injection_detected": is_inj}
    violations = _get_auditor().audit(action, ctx)
    rule = violations[0].rule_id if violations else None

    if is_inj:
        verdict = "QUARANTINE" if score >= 0.9 else "BLOCK"
    elif violations:
        verdict = "WARN"
    else:
        verdict = "APPROVE"
    timeline.append({"step": "policy", "ok": not violations,
                     "detail": f"{rule or 'clean'} → {verdict}"})

    audit_id = str(uuid.uuid4())
    viol_list = [{"rule_id": v.rule_id, "description": v.description} for v in violations]
    out = {
        "verdict": verdict,
        "injection_score": round(score, 4),
        "rule_fired": rule,
        "policy": {"engine": "OPA/Rego", "violations": viol_list},
        "audit_id": audit_id,
        "timeline": timeline,
    }
    out["proof"] = build_proof(
        {k: out[k] for k in ("verdict", "injection_score", "rule_fired", "audit_id")},
        timeline, record_id=audit_id, agent_id="eraya-guardian", verdict=verdict.lower(),
    )
    log_verdict = verdict.lower() if verdict.lower() in {"approve", "warn", "block", "quarantine"} else "block"
    _persist_auditlog(audit_id, "cap-requester", dom, action,
                      {"injection_score": score, "payload_preview": payload[:200]},
                      log_verdict, viol_list, out["proof"]["attestation"])
    return out


# ─── Service B — PANJSHIR Grade ──────────────────────────────────────────────

def route_panjshir(output: str, rubric_id: str = "baseline", reference: str | None = None) -> dict:
    audit_id = str(uuid.uuid4())
    provider = "fallback"
    risk = 0.5
    recommendation = "Deterministic grade (LLM unavailable)."
    risks: list[str] = []
    try:
        from core.providers import critic
        action = {"action_id": "grade_deliverable", "output_preview": str(output)[:600], "rubric_id": rubric_id}
        context = {"domain": "generic", "rubric_id": rubric_id, "reference": reference, "risk_score": 0.5}
        review = critic.review(action, context)
        risk = float(review.get("risk_score", 0.5))
        provider = review.get("provider", "critic")
        recommendation = review.get("recommendation", "")
        risks = list(review.get("risks") or [])
    except Exception:
        pass

    score = round(max(0.0, min(100.0, (1.0 - risk) * 100.0)), 1)
    dimensions = [{"name": "overall", "score": score, "rationale": recommendation}]
    for r in risks[:3]:
        dimensions.append({"name": "concern", "score": score, "rationale": r})
    rubric_hash = "sha256:" + hashlib.sha256((rubric_id or "baseline").encode()).hexdigest()[:32]
    timeline = [{"step": "reviewed", "ok": True, "score": score,
                 "detail": f"critic({provider}) risk={round(risk, 3)}"}]
    out = {
        "score": score,
        "dimensions": dimensions,
        "rubric_hash": rubric_hash,
        "audit_id": audit_id,
        "provider": provider,
    }
    out["proof"] = build_proof(
        {"score": score, "rubric_hash": rubric_hash, "audit_id": audit_id},
        timeline, record_id=audit_id, agent_id="eraya-panjshir", verdict="graded",
    )
    _persist_auditlog(audit_id, "cap-requester", "generic",
                      {"action_id": "grade", "rubric_id": rubric_id},
                      {"score": score}, "approve", [], out["proof"]["attestation"])
    return out


# ─── Service dispatcher ──────────────────────────────────────────────────────

def route_service(service_id: str, body: dict) -> tuple[str, dict]:
    """Map a CAP service_id to its pipeline. Returns (kind, normalized_output)."""
    if service_id == facade.panjshir_service_id() or "panjshir" in (service_id or "").lower():
        return "panjshir", route_panjshir(
            body.get("output") or body.get("payload") or "",
            rubric_id=body.get("rubric_id", "baseline"),
            reference=body.get("reference"),
        )
    # default: KAVACHA Scan
    return "kavacha", route_kavacha(
        body.get("payload") or body.get("output") or "",
        domain=body.get("domain", "generic"),
        policy_pack=body.get("policy_pack", "baseline"),
    )
