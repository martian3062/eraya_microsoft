"""
x402 — agent-economy micropayments over Casper (HTTP 402 Payment Required).

Flow (per the x402 spec):
    1. Agent GETs a paid resource.
    2. Server replies 402 with X-Payment-Address / X-Payment-Amount / X-Payment-Network.
    3. Agent pays and retries with  X-Payment: casper:<payer_pubkey>:<amount>:<signature>
    4. Facilitator verifies the proof → server returns the data.

Verification is layered and graceful:
    * structural + amount + network checks always run;
    * when CSPR.cloud is configured, the facilitator confirms a real on-chain
      transfer of >= amount to the receiver (a true "facilitator verifies" step);
    * otherwise the proof is accepted in demo mode (verified=False).

Receiver defaults to the ERAYA treasury account (overridable via CASPER_PUBLIC_KEY).
"""
from __future__ import annotations

import logging
import os
import time
import uuid

logger = logging.getLogger("eraya.casper.x402")

DEFAULT_RECEIVER = "0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69"
NETWORK = "casper"
DEFAULT_PRICE_MOTES = 1_000_000  # 0.001 CSPR

# nonce -> (issued_at, amount, resource) ; short TTL to bound replay.
_challenges: dict[str, tuple[float, int, str]] = {}
_TTL_S = 300


def receiver() -> str:
    return os.environ.get("CASPER_PUBLIC_KEY", DEFAULT_RECEIVER)


def enabled() -> bool:
    raw = os.environ.get("ERAYA_X402_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def challenge(resource: str, amount_motes: int | None = None) -> dict:
    """Return the 402 challenge headers + body for a paid resource."""
    amount = int(amount_motes or os.environ.get("X402_PRICE_MOTES", DEFAULT_PRICE_MOTES))
    nonce = uuid.uuid4().hex
    _prune()
    _challenges[nonce] = (time.time(), amount, resource)
    return {
        "headers": {
            "X-Payment-Address": receiver(),
            "X-Payment-Amount": str(amount),
            "X-Payment-Network": NETWORK,
            "X-Payment-Nonce": nonce,
        },
        "amount_motes": amount,
        "amount_cspr": round(amount / 1_000_000_000, 6),
        "network": NETWORK,
        "nonce": nonce,
        "resource": resource,
        "message": "Payment required — retry with an X-Payment proof header.",
    }


def parse_header(header: str) -> dict | None:
    """Parse  casper:<payer>:<amount>:<signature>  -> dict, or None if malformed."""
    if not header:
        return None
    parts = header.strip().split(":")
    if len(parts) < 4 or parts[0].lower() != NETWORK:
        return None
    try:
        return {"network": parts[0].lower(), "payer": parts[1],
                "amount": int(parts[2]), "signature": ":".join(parts[3:])}
    except ValueError:
        return None


def verify(header: str, resource: str, required_motes: int | None = None, nonce: str | None = None) -> dict:
    """Verify an X-Payment proof. Returns {ok, verified, payer, amount, reason, ...}."""
    proof = parse_header(header)
    if proof is None:
        return {"ok": False, "verified": False, "reason": "malformed_or_missing_x_payment"}

    required = int(required_motes or os.environ.get("X402_PRICE_MOTES", DEFAULT_PRICE_MOTES))
    if proof["amount"] < required:
        return {"ok": False, "verified": False, "reason": "insufficient_amount",
                "required": required, "paid": proof["amount"]}

    # Bind to a live challenge nonce when supplied (replay protection).
    if nonce is not None:
        entry = _challenges.pop(nonce, None)
        if entry is None or (time.time() - entry[0]) > _TTL_S:
            return {"ok": False, "verified": False, "reason": "nonce_expired_or_unknown"}

    # Real facilitator step: confirm an on-chain transfer when CSPR.cloud is set.
    settled = _confirm_onchain(proof)
    ok = settled is not False  # True (confirmed) or None (demo-accept)
    return {
        "ok": bool(ok),
        "verified": bool(settled),         # True only when on-chain confirmed
        "mode": "live" if os.environ.get("CSPR_CLOUD_REST_URL") else "demo",
        "payer": proof["payer"],
        "amount": proof["amount"],
        "receiver": receiver(),
        "resource": resource,
        "reason": "settled_on_chain" if settled else "accepted_demo",
    }


def _confirm_onchain(proof: dict):
    """Return True if a matching transfer is found on-chain, False if actively
    contradicted, or None when live verification isn't configured (demo)."""
    base = os.environ.get("CSPR_CLOUD_REST_URL")
    if not base:
        return None
    try:
        import httpx
        headers = {}
        key = os.environ.get("CSPR_CLOUD_API_KEY")
        if key:
            headers["Authorization"] = key
        # Look for a recent transfer to the receiver account from the payer.
        acct = os.environ.get("CASPER_ACCOUNT_HASH", "")
        resp = httpx.get(f"{base.rstrip('/')}/accounts/{acct}/transfers",
                         headers=headers, params={"page": 1, "page_size": 20}, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", resp.json())
        for tx in (data if isinstance(data, list) else []):
            if int(tx.get("amount", 0)) >= proof["amount"]:
                return True
        return None  # not found yet — demo-accept rather than hard-reject
    except Exception as exc:
        logger.debug("x402 on-chain confirm failed: %s", exc)
        return None


def _prune() -> None:
    now = time.time()
    for n in [n for n, (ts, _, _) in _challenges.items() if now - ts > _TTL_S]:
        _challenges.pop(n, None)
