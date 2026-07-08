"""
CAP (CROO Agent Protocol) gateway — external A2A commerce on Base/USDC.

This is a NEW surface parallel to the MCP server and the internal x402 bus.
It does NOT rebuild KAVACHA — it routes CAP orders into the existing
security/critic pipelines and reuses AuditSigner (ERAYA_AUDIT_KEY) as the
CAP delivery attestation. Follows ERAYA's graceful-fallback facade rule:
unset CROO_SDK_KEY ⇒ deterministic demo mode; the swarm never hard-depends
on CROO.

Keep CAP separate from core/casper/x402.py (internal Casper micropayments).
"""
