"""
CAP DeliverOrder proof — reuse ERAYA's AuditSigner as the CAP attestation.

CAP's DeliverOrder demands {result_hash, execution_log, attestation}. ERAYA
already emits exactly that on every Guardian decision (HMAC-SHA256 over the
record). This module serializes that into the SDK's proof shape — NO new
proof system, NO second HMAC key (reuses ERAYA_AUDIT_KEY via AuditSigner).
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import uuid

from core.agents.guardian import AuditSigner

_signer: AuditSigner | None = None


def _get_signer() -> AuditSigner:
    global _signer
    if _signer is None:
        _signer = AuditSigner()
    return _signer


def canonical(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def result_hash(output: dict) -> str:
    return "sha256:" + hashlib.sha256(canonical(output).encode()).hexdigest()


def build_proof(output: dict, timeline: list, *, record_id: str | None = None,
                agent_id: str = "eraya-guardian", verdict: str = "delivered") -> dict:
    """Return the CAP DeliverOrder proof block for a delivered output."""
    rid = record_id or str(uuid.uuid4())
    rhash = result_hash(output)
    record = {
        "record_id": rid,
        "agent_id": agent_id,
        "output_hash": rhash,
        "verdict": verdict,
        "timestamp": time.time(),
    }
    attestation = _get_signer().sign(record)
    return {
        "result_hash": rhash,
        "execution_log": timeline,
        "attestation": attestation,
        "audit_key_id": os.environ.get("ERAYA_AUDIT_KEY_ID", "eraya-audit-v1"),
        "record_id": rid,
    }
