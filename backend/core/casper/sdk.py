"""
Casper Python SDK layer — key handling and chain reads for the ERAYA swarm.

Split by what each half is actually good at:

* **pycspr** owns the cryptography. Account-hash derivation and signing are the
  security-critical steps, so they run through the official SDK rather than a
  hand-rolled blake2b. `account_hash()` is used by the x402 facilitator to decide
  whether a payment really landed in our purse — exactly the place where a
  home-made derivation would be a liability.

* **Direct JSON-RPC over HTTPS** owns the node reads. pycspr 0.12's
  `NodeConnection` builds `http://<host>:<port>/rpc`, so it cannot talk to a
  TLS Casper 2.0 endpoint like `node.testnet.casper.network`, and its RPC surface
  is still Casper 1.x-shaped (`info_get_deploy` rather than
  `info_get_transaction`). Rather than pretend otherwise, node calls are made
  against the 2.0 API directly.

Everything degrades gracefully: if pycspr is missing, `account_hash()` falls back
to the equivalent blake2b derivation, which is verified against pycspr in
`tests/test_casper_sdk.py`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request

logger = logging.getLogger("eraya.casper.sdk")

_ALGO_NAME = {"01": b"ed25519", "02": b"secp256k1"}

try:  # the SDK is optional — the swarm must run without it
    import pycspr
    from pycspr import crypto as _pycspr_crypto

    _HAVE_PYCSPR = True
except Exception:  # pragma: no cover - import guard
    pycspr = None
    _pycspr_crypto = None
    _HAVE_PYCSPR = False


def sdk_available() -> bool:
    """True when pycspr is importable and doing the crypto."""
    return _HAVE_PYCSPR


def node_url() -> str:
    return os.environ.get("CASPER_NODE_RPC_URL", "https://node.testnet.casper.network/rpc")


def chain_name() -> str:
    return os.environ.get("CASPER_CHAIN_NAME", "casper-test")


# ── crypto (pycspr) ──────────────────────────────────────────────────────────

def account_hash(public_key_hex: str) -> str | None:
    """Casper account hash for a hex public key, e.g. 'account-hash-cbd9…'.

    Prefers pycspr; falls back to blake2b256(algo || 0x00 || key_bytes), which is
    the same construction the SDK uses.
    """
    key = (public_key_hex or "").strip().lower()
    if len(key) < 4 or key[:2] not in _ALGO_NAME:
        return None

    if _HAVE_PYCSPR:
        try:
            raw = pycspr.get_account_hash(bytes.fromhex(key))
            return "account-hash-" + (raw.hex() if isinstance(raw, (bytes, bytearray)) else str(raw))
        except Exception as exc:  # malformed key, SDK change — fall through
            logger.debug("pycspr account hash failed for %s…: %s", key[:10], exc)

    try:
        digest = hashlib.blake2b(digest_size=32)
        digest.update(_ALGO_NAME[key[:2]] + b"\x00" + bytes.fromhex(key[2:]))
        return "account-hash-" + digest.hexdigest()
    except ValueError:
        return None


def key_status() -> dict:
    """Describe the configured signing key. Never returns private material."""
    path = os.environ.get("CASPER_SECRET_KEY_PATH", "")
    out = {
        "sdk": "pycspr" if _HAVE_PYCSPR else "fallback",
        "sdk_version": getattr(pycspr, "__version__", None) if _HAVE_PYCSPR else None,
        "key_path_configured": bool(path),
        "key_present": bool(path) and os.path.exists(path),
        "public_key": None,
        "account_hash": None,
        "algorithm": None,
    }
    if not (_HAVE_PYCSPR and out["key_present"]):
        pub = os.environ.get("CASPER_PUBLIC_KEY")
        if pub:
            out["public_key"] = pub
            out["account_hash"] = account_hash(pub)
        return out

    for algo in (pycspr.KeyAlgorithm.SECP256K1, pycspr.KeyAlgorithm.ED25519):
        try:
            key = pycspr.parse_private_key(path, algo)
            out["public_key"] = key.account_key.hex()
            out["account_hash"] = account_hash(key.account_key.hex())
            out["algorithm"] = algo.name
            return out
        except Exception:
            continue
    logger.debug("could not parse signing key at %s with either algorithm", path)
    return out


def sign(payload: bytes) -> str | None:
    """Sign bytes with the configured key. Returns hex, or None if unavailable."""
    path = os.environ.get("CASPER_SECRET_KEY_PATH", "")
    if not (_HAVE_PYCSPR and path and os.path.exists(path)):
        return None
    for algo in (pycspr.KeyAlgorithm.SECP256K1, pycspr.KeyAlgorithm.ED25519):
        try:
            key = pycspr.parse_private_key(path, algo)
            return key.get_signature(payload).hex()
        except Exception:
            continue
    return None


def verify(payload: bytes, signature_hex: str, public_key_hex: str) -> bool:
    """Verify a signature produced by `sign()`.

    Casper account keys carry a one-byte algorithm prefix (01 ed25519 /
    02 secp256k1); pycspr wants the raw key plus the algorithm, so split them.
    """
    if not _HAVE_PYCSPR:
        return False
    key = (public_key_hex or "").strip().lower()
    if len(key) < 4 or key[:2] not in _ALGO_NAME:
        return False
    algo = (pycspr.KeyAlgorithm.ED25519 if key[:2] == "01"
            else pycspr.KeyAlgorithm.SECP256K1)
    try:
        return bool(_pycspr_crypto.is_signature_valid(
            payload, bytes.fromhex(signature_hex), bytes.fromhex(key[2:]), algo))
    except Exception as exc:
        logger.debug("signature verify failed: %s", exc)
        return False


# ── node reads (Casper 2.0 JSON-RPC) ─────────────────────────────────────────

def rpc(method: str, params: dict | list | None = None, timeout: int = 15) -> dict:
    """One JSON-RPC round trip. Returns {'result': …} or {'error': …}."""
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    try:
        req = urllib.request.Request(
            node_url(), data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.load(resp)
    except Exception as exc:
        logger.debug("rpc %s failed: %s", method, exc)
        return {"error": {"message": str(exc), "method": method}}


def balance(public_key_hex: str | None = None) -> dict:
    """Main-purse balance for an account."""
    pub = public_key_hex or os.environ.get("CASPER_PUBLIC_KEY", "")
    if not pub:
        return {"ok": False, "error": "no public key configured"}
    res = rpc("query_balance", {"purse_identifier": {"main_purse_under_public_key": pub}})
    if "result" not in res:
        return {"ok": False, "error": res.get("error", {}).get("message", "rpc failed"),
                "public_key": pub}
    motes = int(res["result"]["balance"])
    return {
        "ok": True,
        "public_key": pub,
        "account_hash": account_hash(pub),
        "motes": motes,
        "cspr": round(motes / 1_000_000_000, 4),
        "network": chain_name(),
    }


def transaction(tx_hash: str) -> dict:
    """Look up a transaction, trying both Casper 2.0 identifier shapes."""
    for ident in ({"Version1": tx_hash}, {"Deploy": tx_hash}):
        res = rpc("info_get_transaction",
                  {"transaction_hash": ident, "finalized_approvals": True})
        if "result" not in res:
            continue
        info = res["result"].get("execution_info") or {}
        exec_result = (info.get("execution_result") or {}).get("Version2") or {}
        transfers = []
        for entry in exec_result.get("transfers") or []:
            t = entry.get("Version2") or entry.get("Version1") or {}
            frm = t.get("from")
            transfers.append({
                "from": frm.get("AccountHash") if isinstance(frm, dict) else frm,
                "to": t.get("to"),
                "motes": t.get("amount"),
            })
        return {
            "ok": True,
            "tx_hash": tx_hash,
            "kind": "Deploy" if "Deploy" in ident else "Version1",
            "block_height": info.get("block_height"),
            "success": exec_result.get("error_message") is None,
            "error_message": exec_result.get("error_message"),
            "cost_cspr": round(int(exec_result.get("cost", 0)) / 1_000_000_000, 4),
            "transfers": transfers,
            "explorer_url": f"https://testnet.cspr.live/transaction/{tx_hash}",
        }
    return {"ok": False, "tx_hash": tx_hash, "error": "transaction not found on chain"}


def account_named_keys(public_key_hex: str | None = None) -> dict:
    """Named keys on an account — where installed contract hashes show up."""
    pub = public_key_hex or os.environ.get("CASPER_PUBLIC_KEY", "")
    res = rpc("state_get_account_info", {"public_key": pub})
    if "result" not in res:
        return {"ok": False, "error": res.get("error", {}).get("message", "rpc failed")}
    acct = res["result"]["account"]
    return {
        "ok": True,
        "public_key": pub,
        "account_hash": acct.get("account_hash"),
        "named_keys": {k["name"]: k["key"] for k in acct.get("named_keys", [])},
    }


def chain_status() -> dict:
    """Node/chain health — proves the RPC endpoint is a real, synced node."""
    res = rpc("info_get_status")
    if "result" not in res:
        return {"ok": False, "error": res.get("error", {}).get("message", "rpc failed")}
    r = res["result"]
    block = (r.get("last_added_block_info") or {})
    return {
        "ok": True,
        "node_url": node_url(),
        "chain_name": r.get("chainspec_name"),
        "api_version": r.get("api_version"),
        "build_version": r.get("build_version"),
        "block_height": block.get("height"),
        "block_hash": block.get("hash"),
        "peers": len(r.get("peers", [])),
    }
