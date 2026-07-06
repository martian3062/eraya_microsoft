"""
On-chain anchoring of KAVACHA anomalies to Casper testnet.

When a funded testnet key (`CASPER_SECRET_KEY_PATH`) and node RPC
(`CASPER_NODE_RPC_URL`) are configured, a high-severity anomaly is anchored as a
real testnet transaction whose transfer-id encodes the evidence-hash prefix —
producing a verifiable https://testnet.cspr.live/deploy/<hash> link. Without
those env vars every call is a no-op (demo mode), so the live site is unaffected.

Casper-version note: pycspr 1.2.0 targets Casper 1.x native transfers. If the
testnet is Casper 2.0 (Condor), only `_submit_transfer()` needs updating — the
public interface (`anchoring_enabled`, `anchor_anomaly`) is stable.

Default account (overridable via env):
    CASPER_PUBLIC_KEY   = 0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69
    CASPER_ACCOUNT_HASH = cbd9021f24d2c5c494a8f6fd645b151dc09d69671b3ca9ffc866396be0b7e77f
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from urllib.parse import urlparse

logger = logging.getLogger("eraya.casper.anchor")

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


def _rpc_host_port(rpc_url: str) -> tuple[str, int]:
    parsed = urlparse(rpc_url if "://" in rpc_url else f"http://{rpc_url}")
    return parsed.hostname or "127.0.0.1", parsed.port or 7777


def _submit_transfer(transfer_id: int) -> str | None:
    """Build, sign, and send a native self-transfer carrying `transfer_id`.

    Isolated so the Casper-1.x vs 2.0 details live in one place.
    """
    import pycspr

    key_path = os.environ["CASPER_SECRET_KEY_PATH"]
    algo_name = os.environ.get("CASPER_SECRET_KEY_ALGO", "SECP256K1").upper()
    chain = os.environ.get("CASPER_CHAIN_NAME", "casper-test")
    host, port = _rpc_host_port(os.environ["CASPER_NODE_RPC_URL"])

    algo = getattr(pycspr.KeyAlgorithm, algo_name)
    keypair = pycspr.parse_private_key(key_path, algo)

    client = pycspr.NodeClient(pycspr.NodeConnectionInfo(host=host, port_rpc=port))

    params = pycspr.create_deploy_parameters(account=keypair, chain_name=chain)
    deploy = pycspr.create_transfer(
        params,
        amount=_ANCHOR_AMOUNT_MOTES,
        target=keypair.account_key,   # self-transfer (evidence anchor, funds returned)
        correlation_id=transfer_id,
    )
    deploy.approve(keypair)
    client.send_deploy(deploy)
    return deploy.hash.hex() if hasattr(deploy.hash, "hex") else str(deploy.hash)


def status() -> dict:
    return {
        "enabled": anchoring_enabled(),
        "account_hash": os.environ.get(
            "CASPER_ACCOUNT_HASH",
            "cbd9021f24d2c5c494a8f6fd645b151dc09d69671b3ca9ffc866396be0b7e77f",
        ),
        "network": os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
    }
