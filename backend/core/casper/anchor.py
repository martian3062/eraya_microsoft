"""
On-chain anchoring of KAVACHA anomalies to Casper testnet.

When a funded testnet key (`CASPER_SECRET_KEY_PATH`) and node RPC
(`CASPER_NODE_RPC_URL`) are configured, a high-severity anomaly is anchored as a
real testnet transaction whose transfer-id encodes the evidence-hash prefix —
producing a verifiable https://testnet.cspr.live/deploy/<hash> link. Without
those env vars every call is a no-op (demo mode), so the live site is unaffected.

Signing uses the canonical `casper-client` CLI via subprocess (set
`CASPER_CLIENT_BIN` to override the path). This is version-robust across Casper
1.x / 2.0 — only the CLI flags would change. The public interface
(`anchoring_enabled`, `anchor_anomaly`) is stable regardless.

Default account (overridable via env):
    CASPER_PUBLIC_KEY   = 0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69
    CASPER_ACCOUNT_HASH = cbd9021f24d2c5c494a8f6fd645b151dc09d69671b3ca9ffc866396be0b7e77f
"""
from __future__ import annotations

import hashlib
import logging
import os
import time

logger = logging.getLogger("eraya.casper.anchor")

_DEFAULT_PUBLIC_KEY = "0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69"
_ANCHOR_AMOUNT_MOTES = 2_500_000_000  # 2.5 CSPR self-transfer (min native transfer)
_RATE_LIMIT_S = 300                    # at most one anchor per anomaly type / 5 min
_last_anchor: dict[str, float] = {}


def anchoring_enabled() -> bool:
    return bool(os.environ.get("CASPER_SECRET_KEY_PATH") and os.environ.get("CASPER_NODE_RPC_URL"))


def evidence_hash(finding: dict) -> str:
    """Deterministic SHA-256 over the anomaly's type + evidence."""
    payload = finding.get("type", "") + "|" + repr(sorted((finding.get("evidence") or {}).items()))
    return hashlib.sha256(payload.encode()).hexdigest()


def _hash_to_transfer_id(h: str) -> int:
    # Casper transfer-id is a u64; take the top 15 hex chars to stay in range.
    return int(h[:15], 16)


def anchor_anomaly(finding: dict) -> dict | None:
    """Anchor one anomaly on-chain. Returns a record dict or None (demo/rate-limited)."""
    if not anchoring_enabled():
        return None
    kind = finding.get("type", "anomaly")
    now = time.time()
    if now - _last_anchor.get(kind, 0.0) < _RATE_LIMIT_S:
        return None

    ev = evidence_hash(finding)
    transfer_id = _hash_to_transfer_id(ev)
    try:
        deploy_hash = _submit_transfer(transfer_id)
    except Exception as exc:  # never break the request path
        logger.warning("anomaly anchor submit failed: %s", exc)
        return None
    if not deploy_hash:
        return None

    _last_anchor[kind] = now
    return {
        "anomaly_type": kind,
        "severity": finding.get("severity"),
        "evidence_hash": ev,
        "transfer_id": transfer_id,
        "deploy_hash": deploy_hash,
        "explorer_url": f"https://testnet.cspr.live/deploy/{deploy_hash}",
        "network": os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
        "anchored_at": now,
    }


def _submit_transfer(transfer_id: int) -> str | None:
    """Send a native self-transfer carrying `transfer_id` via casper-client.

    Isolated so all Casper CLI specifics live in one place. Returns the deploy
    hash on success, else None.
    """
    import json
    import subprocess

    key_path = os.environ["CASPER_SECRET_KEY_PATH"]
    rpc = os.environ["CASPER_NODE_RPC_URL"]
    chain = os.environ.get("CASPER_CHAIN_NAME", "casper-test")
    target = os.environ.get("CASPER_PUBLIC_KEY", _DEFAULT_PUBLIC_KEY)  # self-transfer
    client_bin = os.environ.get("CASPER_CLIENT_BIN", "casper-client")

    cmd = [
        client_bin, "transfer",
        "--node-address", rpc,
        "--chain-name", chain,
        "--secret-key", key_path,
        "--amount", str(_ANCHOR_AMOUNT_MOTES),
        "--target-account", target,
        "--transfer-id", str(transfer_id),
        "--payment-amount", os.environ.get("CASPER_TRANSFER_PAYMENT_MOTES", "100000000"),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
    if proc.returncode != 0:
        logger.warning("casper-client transfer failed: %s", (proc.stderr or "")[:200])
        return None
    try:
        return json.loads(proc.stdout).get("result", {}).get("deploy_hash")
    except Exception:
        return None


def status() -> dict:
    return {
        "enabled": anchoring_enabled(),
        "account_hash": os.environ.get(
            "CASPER_ACCOUNT_HASH",
            "cbd9021f24d2c5c494a8f6fd645b151dc09d69671b3ca9ffc866396be0b7e77f",
        ),
        "network": os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
    }
