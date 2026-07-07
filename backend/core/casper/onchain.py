"""
Real on-chain treasury data from the Casper testnet RPC.

Queries live account balances via the JSON-RPC `query_balance` method (Casper
2.0) so the dashboard shows the *actual* funded balance instead of a mock TVL.
Graceful: returns None / empty when the RPC or accounts are unset.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("eraya.casper.onchain")

# Fallback identities (overridable via env).
_TREASURY_PK = "0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69"
_OPS_PK = "0122c68722c85ee2eb5d6cdba98076817a6af821835eade23012bc64317dc8b0b1"
CSPR_PRICE_USD = 0.0234
MOTES_PER_CSPR = 1_000_000_000


def _rpc(method: str, params: dict):
    rpc = os.environ.get("CASPER_NODE_RPC_URL")
    if not rpc:
        return None
    try:
        import httpx
        resp = httpx.post(rpc, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params}, timeout=15)
        resp.raise_for_status()
        return resp.json().get("result")
    except Exception as exc:
        logger.warning("RPC %s failed: %s", method, exc)
        return None


_price_cache = {"ts": 0.0, "usd": None}


def cspr_price_usd() -> float:
    """Live CSPR/USD price (CoinGecko), cached ~5 min. Falls back to env/default."""
    import time
    default = float(os.environ.get("CSPR_PRICE_USD", CSPR_PRICE_USD))
    now = time.time()
    if _price_cache["usd"] is not None and now - _price_cache["ts"] < 300:
        return _price_cache["usd"]
    try:
        import httpx
        resp = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "casper-network", "vs_currencies": "usd"},
            timeout=8,
        )
        resp.raise_for_status()
        price = float(resp.json()["casper-network"]["usd"])
        if price > 0:
            _price_cache.update(ts=now, usd=price)
            return price
    except Exception as exc:
        logger.warning("CSPR price fetch failed: %s", exc)
    return _price_cache["usd"] or default


def balance_motes(public_key: str):
    res = _rpc("query_balance", {"purse_identifier": {"main_purse_under_public_key": public_key}})
    if not res:
        return None
    try:
        return int(res.get("balance"))
    except Exception:
        return None


def send_transfer(target: str, amount_motes: int, memo_id: int | None = None) -> dict:
    """Real on-chain CSPR transfer (bot pay). Returns {ok, tx, explorer_url,...}."""
    import json
    import random
    import subprocess

    key = os.environ.get("CASPER_SECRET_KEY_PATH")
    rpc = os.environ.get("CASPER_NODE_RPC_URL")
    if not (key and rpc):
        return {"ok": False, "error": "signing not configured (need key + RPC)"}
    memo = memo_id if memo_id is not None else random.randint(1, 10 ** 9)
    client = os.environ.get("CASPER_CLIENT_BIN", "casper-client")
    cmd = [
        client, "put-transaction", "transfer",
        "--node-address", rpc, "--chain-name", os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
        "--secret-key", key, "--target", target,
        "--transfer-amount", str(int(amount_motes)), "--id", str(memo),
        "--pricing-mode", "classic", "--payment-amount", "100000000",
        "--gas-price-tolerance", "1", "--standard-payment", "true",
    ]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if p.returncode != 0:
            return {"ok": False, "error": (p.stderr or "")[:200]}
        d = json.loads(p.stdout).get("result", {})
        th = d.get("transaction_hash") or d.get("deploy_hash")
        if isinstance(th, dict):
            th = next(iter(th.values()), None)
        return {"ok": True, "tx": th, "memo_id": memo,
                "amount_cspr": round(int(amount_motes) / MOTES_PER_CSPR, 4), "target": target,
                "explorer_url": f"https://testnet.cspr.live/transaction/{th}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:200]}


def snapshot() -> dict:
    """Real treasury snapshot: live balances of the swarm's Casper accounts."""
    treasury_pk = os.environ.get("CASPER_ANCHOR_RECIPIENT", _TREASURY_PK)
    ops_pk = os.environ.get("CASPER_PUBLIC_KEY", _OPS_PK)
    price = cspr_price_usd()

    accounts, total_cspr = [], 0.0
    for label, pk in (("Treasury", treasury_pk), ("Swarm ops", ops_pk)):
        m = balance_motes(pk)
        if m is None:
            continue
        cspr = m / MOTES_PER_CSPR
        total_cspr += cspr
        accounts.append({
            "label": label, "public_key": pk,
            "balance_motes": m, "balance_cspr": round(cspr, 4),
            "balance_usd": round(cspr * price, 2),
            "explorer_url": f"https://testnet.cspr.live/account/{pk}",
        })

    from core.casper import anchor
    try:
        from core.casper.mcp import CasperMCPClient
        validators = CasperMCPClient().get_validators()[:8]
    except Exception:
        validators = []
    return {
        "network": os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
        "live": bool(accounts),
        "cspr_price_usd": price,
        "accounts": accounts,
        "total_cspr": round(total_cspr, 4),
        "total_usd": round(total_cspr * price, 2),
        "validators": validators,
        "recent_anchors": anchor.recent(),
    }
