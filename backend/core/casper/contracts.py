"""
Deployed-contract registry for the ERAYA Odra contracts.

The contracts live in `contracts/` (AgentRegistry + TradePolicy, Odra).
Once deployed (scripts/build_deploy_contracts.sh deploy), export:

    CASPER_AGENT_REGISTRY_HASH=hash-…
    CASPER_TRADE_POLICY_HASH=hash-…

and every surface (Quant Desk header, dashboard) picks up the explorer links.
Until then this reports them as pending — same graceful-facade contract the
rest of the Casper layer follows.
"""
from __future__ import annotations

import os


def _entry(env_var: str, name: str) -> dict:
    h = os.environ.get(env_var, "")
    return {
        "name": name,
        "deployed": bool(h),
        "hash": h or None,
        "explorer_url": f"https://testnet.cspr.live/contract-package/{h.removeprefix('hash-')}" if h else None,
    }


def status() -> dict:
    registry = _entry("CASPER_AGENT_REGISTRY_HASH", "AgentRegistry")
    policy = _entry("CASPER_TRADE_POLICY_HASH", "TradePolicy")
    return {
        "network": os.environ.get("CASPER_CHAIN_NAME", "casper-test"),
        "framework": "odra",
        "source": "contracts/",
        "agent_registry": registry,
        "trade_policy": policy,
        "deployed": registry["deployed"] and policy["deployed"],
    }
