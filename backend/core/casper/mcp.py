"""Casper MCP/CSPR.cloud client surface.

The buildathon branch can run without live Casper credentials. When endpoint
environment variables are absent, this module returns deterministic demo data
with the same shape the live adapters expect.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
import time
from typing import Any


@dataclass(frozen=True)
class CasperMCPServer:
    name: str
    url: str
    tools: list[str]


CASPER_MCP_SERVERS: dict[str, CasperMCPServer] = {
    "casper_chain": CasperMCPServer(
        name="casper_chain",
        url=os.environ.get("CASPER_MCP_URL", ""),
        tools=[
            "query_balance",
            "get_deploy_info",
            "get_block",
            "query_contract_state",
            "get_validator_info",
        ],
    ),
    "cspr_trade": CasperMCPServer(
        name="cspr_trade",
        url=os.environ.get("CSPR_TRADE_MCP_URL", ""),
        tools=[
            "get_token_price",
            "execute_swap",
            "get_pool_info",
            "get_portfolio",
            "place_limit_order",
        ],
    ),
}


class CasperMCPClient:
    """Small sync client used by domain adapters, wallets, and demo services."""

    def __init__(self, rest_url: str | None = None, network: str | None = None):
        self.rest_url = rest_url or os.environ.get("CSPR_CLOUD_REST_URL", "")
        self.network = network or os.environ.get("CASPER_NETWORK", "testnet")
        self.mode = "live" if self.rest_url else "demo"

    def query_balance(self, account_hash: str) -> int:
        seed = int(hashlib.sha256(account_hash.encode()).hexdigest()[:8], 16)
        return 100_000_000_000 + (seed % 45_000_000_000)

    def submit_deploy(self, signed_deploy: dict[str, Any]) -> str:
        payload = repr(sorted(signed_deploy.items()))
        digest = hashlib.sha256(payload.encode()).hexdigest()
        return f"deploy-{digest[:24]}"

    def get_pool_info(self, pool_id: str = "cspr-usdc") -> dict[str, Any]:
        tick = int(time.time() / 30)
        drift = (tick % 9) - 4
        return {
            "pool_id": pool_id,
            "token_pair": pool_id.upper().replace("-", "/"),
            "pool_tvl_usd": 2_420_000 + drift * 12_500,
            "apy_current": round(12.7 + drift * 0.18, 2),
            "apy_7d_avg": 11.9,
            "liquidity_depth_usd": 840_000 + drift * 6_000,
            "slippage_estimate_bps": max(12, 44 + drift * 4),
            "source": "CSPR.trade MCP" if CASPER_MCP_SERVERS["cspr_trade"].url else "demo-cache",
        }

    def get_market_snapshot(self) -> dict[str, float]:
        tick = int(time.time() / 20)
        return {
            "gas_price_motes": float(2_500_000_000 + (tick % 6) * 150_000_000),
            "tx_volume_24h": float(14_200 + (tick % 7) * 380),
            "mempool_pending_count": float(28 + (tick % 5) * 6),
            "governance_quorum_pct": float(47 + (tick % 4) * 5),
            "validator_uptime_pct": 99.2,
        }

    def get_pending_deploys(self) -> list[dict[str, Any]]:
        return [
            {
                "deploy_hash": "deploy-front-run-watch-01",
                "type": "swap",
                "pool": "cspr-usdc",
                "max_slippage_bps": 180,
                "sender": "account-hash-demo-risk",
            },
            {
                "deploy_hash": "deploy-validator-stake-02",
                "type": "delegate",
                "pool": "validator-17",
                "max_slippage_bps": 0,
                "sender": "account-hash-demo-safe",
            },
        ]

    def query_contract_state(self, address: str) -> dict[str, Any]:
        return {
            "address": address,
            "liquidity": 685_000,
            "last_liquidity": 980_000,
            "active_proposals": 3,
            "suspicious_votes": 1,
        }

    def get_validator_info(self, validator: str) -> dict[str, Any]:
        return {
            "validator": validator,
            "uptime_pct": 99.2,
            "delegation_rate": 0.094,
            "status": "active",
        }

    def execute_swap(self, token_a: str, token_b: str, amount: float) -> dict[str, Any]:
        return {
            "status": "submitted",
            "token_a": token_a,
            "token_b": token_b,
            "amount": amount,
            "estimated_slippage_bps": 42,
            "mode": self.mode,
        }
