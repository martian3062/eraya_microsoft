"""
A2A message signature verification — shared helper used by both the WebSocket
consumer and the security simulation endpoints.

Single source of truth: delegates entirely to AuditSigner (HMAC-SHA256).
Never duplicates the signing logic.
"""
from __future__ import annotations

from core.agents.guardian import AuditSigner

# Module-level signer uses ERAYA_AUDIT_KEY env var (same key the rest of the
# framework uses).  Do NOT instantiate with a custom key here.
_canonical_signer = AuditSigner()


def verify_a2a_message(message_data: dict, presented_sig: str) -> bool:
    """
    Verify a presented HMAC-SHA256 signature against the canonical ERAYA_AUDIT_KEY.
    Uses hmac.compare_digest internally — timing-safe.
    """
    return _canonical_signer.verify(message_data, presented_sig)


def sign_a2a_message(message_data: dict) -> str:
    """Sign an A2A message payload with the canonical ERAYA_AUDIT_KEY."""
    return _canonical_signer.sign(message_data)
