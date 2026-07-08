"""Pydantic in/out schemas for the two CAP services (§3 of the spec)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class CapProof(BaseModel):
    result_hash: str
    execution_log: list[dict] = Field(default_factory=list)
    attestation: str
    audit_key_id: str = "eraya-audit-v1"
    record_id: Optional[str] = None


# ─── Service A — KAVACHA Scan (Data & Verification) ──────────────────────────

class KavachaScanIn(BaseModel):
    payload: str
    domain: str = "generic"
    source_agent_did: Optional[str] = None
    policy_pack: str = "baseline"


class KavachaScanOut(BaseModel):
    verdict: str  # APPROVE | WARN | BLOCK | QUARANTINE
    injection_score: float = 0.0
    rule_fired: Optional[str] = None
    policy: dict = Field(default_factory=dict)
    audit_id: str
    timeline: list[dict] = Field(default_factory=list)
    proof: CapProof


# ─── Service B — PANJSHIR Grade (Developer Tooling) ──────────────────────────

class PanjshirGradeIn(BaseModel):
    output: str
    rubric_id: str = "baseline"
    reference: Optional[str] = None


class PanjshirGradeOut(BaseModel):
    score: float
    dimensions: list[dict] = Field(default_factory=list)
    rubric_hash: str
    audit_id: str
    proof: CapProof
