"""
x402 — agent-economy micropayments over Casper (HTTP 402 Payment Required).

Flow (per the x402 spec):
    1. Agent GETs a paid resource.
    2. Server replies 402 with X-Payment-Address / X-Payment-Amount /
       X-Payment-Network / X-Payment-Nonce.
    3. Agent pays on-chain, then retries with
           X-Payment: casper:<payer_pubkey>:<amount>:<transaction_hash>
    4. The facilitator settles the proof against the Casper node and, only if a
       matching transfer really landed, the server returns the data.

Settlement is verified directly against the Casper JSON-RPC node — no
third-party indexer and no API key. `_settle()` pulls the transaction, checks it
executed without error on the expected chain, and walks its `transfers` for one
that actually moved >= the required motes to this receiver's account hash.

Verification is layered:
    * structural, amount and nonce checks always run;
    * when the proof carries a transaction hash, the node is the arbiter —
      a contradicted proof (failed tx, wrong target, short amount, replayed
      hash) is REJECTED outright;
    * a proof with no transaction hash, or an unreachable node, degrades to
      demo-accept (verified=False) so the walkthrough never hard-fails.

Receiver defaults to the ERAYA treasury account (overridable via CASPER_PUBLIC_KEY).
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
import uuid

logger = logging.getLogger("eraya.casper.x402")

DEFAULT_RECEIVER = "0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69"
NETWORK = "casper"
DEFAULT_PRICE_MOTES = 1_000_000  # 0.001 CSPR

# nonce -> (issued_at, amount, resource) ; short TTL to bound replay.
_challenges: dict[str, tuple[float, int, str]] = {}
_TTL_S = 300

# settlement tx hashes already redeemed -> when. One payment, one resource.
_spent: dict[str, float] = {}
_SPENT_TTL_S = 86_400


def receiver() -> str:
    return os.environ.get("CASPER_PUBLIC_KEY", DEFAULT_RECEIVER)


def node_url() -> str:
    return os.environ.get("CASPER_NODE_RPC_URL", "https://node.testnet.casper.network/rpc")


def chain_name() -> str:
    return os.environ.get("CASPER_CHAIN_NAME", "casper-test")


def enabled() -> bool:
    raw = os.environ.get("ERAYA_X402_ENABLED", "true").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def account_hash(public_key_hex: str) -> str | None:
    """Casper account hash for a public key — derived by pycspr via core.casper.sdk.

    This decides whether a payment landed in *our* purse, so it goes through the
    official SDK rather than a local reimplementation.
    """
    from core.casper import sdk

    return sdk.account_hash(public_key_hex)


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
        "settlement": {
            "chain": chain_name(),
            "receiver_account_hash": account_hash(receiver()),
            "proof_format": "casper:<payer_pubkey>:<amount_motes>:<transaction_hash>",
        },
        "message": "Payment required — retry with an X-Payment proof header.",
    }


def parse_header(header: str) -> dict | None:
    """Parse  casper:<payer>:<amount>:<tx_hash|signature>  -> dict, or None."""
    if not header:
        return None
    parts = header.strip().split(":")
    if len(parts) < 4 or parts[0].lower() != NETWORK:
        return None
    try:
        amount = int(parts[2])
    except ValueError:
        return None
    tail = ":".join(parts[3:]).strip()
    # A bare 64-hex tail is a settlement transaction hash; anything else is
    # carried through as an opaque signature (older clients).
    is_tx = len(tail) == 64 and all(c in "0123456789abcdefABCDEF" for c in tail)
    return {
        "network": parts[0].lower(),
        "payer": parts[1],
        "amount": amount,
        "tx_hash": tail.lower() if is_tx else None,
        "signature": None if is_tx else tail,
    }


def verify(header: str, resource: str, required_motes: int | None = None,
           nonce: str | None = None) -> dict:
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
        required = max(required, entry[1])

    settled, detail = _settle(proof, required)

    if settled is False:
        return {"ok": False, "verified": False, "reason": detail.get("reason", "settlement_rejected"),
                "payer": proof["payer"], "amount": proof["amount"],
                "receiver": receiver(), "resource": resource, "mode": "live", **detail}

    return {
        "ok": True,
        "verified": settled is True,        # True only when the node confirmed it
        "mode": "live" if settled is True else "demo",
        "payer": proof["payer"],
        "amount": proof["amount"],
        "receiver": receiver(),
        "resource": resource,
        "reason": "settled_on_chain" if settled is True else "accepted_demo",
        **detail,
    }


def _settle(proof: dict, required: int) -> tuple[bool | None, dict]:
    """Settle a proof against the Casper node.

    Returns (True, detail)  — a matching transfer really landed;
            (False, detail) — the chain contradicts the proof, reject;
            (None, detail)  — nothing to check against, caller demo-accepts.
    """
    tx_hash = proof.get("tx_hash")
    if not tx_hash:
        return None, {"settlement": "no_transaction_hash_supplied"}

    _prune()
    if tx_hash in _spent:
        return False, {"reason": "transaction_already_redeemed", "tx_hash": tx_hash}

    target = account_hash(receiver())
    if target is None:
        return None, {"settlement": "receiver_account_hash_underivable"}

    status, result = _fetch_transaction(tx_hash)
    if status == "not_found":
        # The node answered and has never seen this hash — the proof is a fake.
        return False, {"reason": "transaction_not_found_on_chain", "tx_hash": tx_hash}
    if status != "found":
        # Node unreachable / timed out — don't punish the payer for our outage.
        return None, {"settlement": "node_unreachable", "tx_hash": tx_hash}

    exec_info = result.get("execution_info") or {}
    exec_result = (exec_info.get("execution_result") or {}).get("Version2") or {}
    if not exec_result:
        return None, {"settlement": "not_yet_executed", "tx_hash": tx_hash}

    if exec_result.get("error_message"):
        return False, {"reason": "transaction_failed_on_chain", "tx_hash": tx_hash,
                       "chain_error": exec_result["error_message"]}

    if not _chain_matches(result):
        return False, {"reason": "wrong_chain", "tx_hash": tx_hash, "expected_chain": chain_name()}

    payer_hash = account_hash(proof["payer"])
    payer_mismatch = False
    for entry in exec_result.get("transfers") or []:
        t = entry.get("Version2") or entry.get("Version1") or {}
        if t.get("to") != target:
            continue
        try:
            moved = int(t.get("amount", 0))
        except (TypeError, ValueError):
            continue
        if moved < required:
            continue
        # Optional payer binding: only enforced when both sides are derivable.
        frm = (t.get("from") or {})
        frm_hash = frm.get("AccountHash") if isinstance(frm, dict) else frm
        if payer_hash and frm_hash and frm_hash != payer_hash:
            payer_mismatch = True
            continue
        _spent[tx_hash] = time.time()
        return True, {
            "settlement": "confirmed",
            "tx_hash": tx_hash,
            "moved_motes": moved,
            "block_height": exec_info.get("block_height"),
            "explorer_url": f"https://testnet.cspr.live/transaction/{tx_hash}",
        }

    if payer_mismatch:
        return False, {"reason": "transfer_not_sent_by_claimed_payer", "tx_hash": tx_hash,
                       "claimed_payer": proof["payer"]}
    return False, {"reason": "no_matching_transfer_to_receiver", "tx_hash": tx_hash,
                   "expected_to": target, "expected_min_motes": required}


def _fetch_transaction(tx_hash: str) -> tuple[str, dict | None]:
    """info_get_transaction, trying both Casper 2.0 identifier shapes.

    Returns ("found", result) | ("not_found", None) | ("unreachable", None).
    The distinction matters: a hash the node has never seen is a forged proof
    and must be rejected, whereas our own network failure must not be.
    """
    answered = False
    for ident in ({"Version1": tx_hash}, {"Deploy": tx_hash}):
        payload = {
            "jsonrpc": "2.0", "id": 1, "method": "info_get_transaction",
            "params": {"transaction_hash": ident, "finalized_approvals": True},
        }
        try:
            req = urllib.request.Request(
                node_url(), data=json.dumps(payload).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.load(resp)
            if "result" in body:
                return "found", body["result"]
            # A JSON-RPC error body still proves the node answered us.
            answered = True
            logger.debug("x402 settle: node rejected %s: %s", ident, body.get("error"))
        except Exception as exc:  # network, timeout, malformed — stay graceful
            logger.debug("x402 settle lookup failed (%s): %s", ident, exc)
    return ("not_found" if answered else "unreachable"), None


def _chain_matches(result: dict) -> bool:
    """True when the transaction was submitted to the chain we settle on."""
    tx = result.get("transaction") or {}
    deploy = tx.get("Deploy")
    if deploy:
        return (deploy.get("header") or {}).get("chain_name") == chain_name()
    v1 = tx.get("Version1")
    if v1:
        payload = v1.get("payload") or v1
        return payload.get("chain_name", chain_name()) == chain_name()
    return True  # unknown shape — don't reject on a schema we can't read


def _prune() -> None:
    now = time.time()
    for n in [n for n, (ts, _, _) in _challenges.items() if now - ts > _TTL_S]:
        _challenges.pop(n, None)
    for h in [h for h, ts in _spent.items() if now - ts > _SPENT_TTL_S]:
        _spent.pop(h, None)
