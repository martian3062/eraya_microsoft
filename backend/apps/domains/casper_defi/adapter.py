"""Casper DeFi domain adapter for the ERAYA swarm."""
from __future__ import annotations

import math
import time
from typing import Any, Iterator

from apps.domains.base import ActionOutcome, DomainAction, ErayaEnvironment, RawSignal
from core.agents.threat_scanner import ThreatScanner
from core.casper.mcp import CASPER_MCP_SERVERS, CasperMCPClient
from core.casper.wallet import AgentWallet
from core.consensus.quorum import demo_quorum_snapshot
from core.reputation.tracker import get_reputation_tracker


class CasperDeFiEnvironment(ErayaEnvironment):
    """Real-shape Casper DeFi adapter with demo-safe live integration hooks."""

    domain_name = "casper_defi"

    def __init__(self, client: CasperMCPClient | None = None):
        self.client = client or CasperMCPClient()
        self.agent_ids = [
            "perceiver-casper-001",
            "planner-casper-001",
            "recoverer-casper-001",
            "guardian-casper-001",
        ]
        self.wallets = {agent_id: AgentWallet(agent_id, self.client) for agent_id in self.agent_ids}
        self.pools = ["cspr-usdc", "cspr-weth", "cspr-btc"]

    def signal_stream(self) -> Iterator[RawSignal]:
        idx = 0
        while True:
            pool_id = self.pools[idx % len(self.pools)]
            pool = self.client.get_pool_info(pool_id)
            market = self.client.get_market_snapshot()
            wave = math.sin(time.time() / 45 + idx)
            features = {
                "pool_tvl_usd": float(pool["pool_tvl_usd"]),
                "apy_current": float(pool["apy_current"]) + wave * 0.2,
                "apy_7d_avg": float(pool["apy_7d_avg"]),
                "gas_price_motes": market["gas_price_motes"],
                "tx_volume_24h": market["tx_volume_24h"],
                "slippage_estimate_bps": float(pool["slippage_estimate_bps"]),
                "liquidity_depth_usd": float(pool["liquidity_depth_usd"]),
                "governance_quorum_pct": market["governance_quorum_pct"],
                "validator_uptime_pct": market["validator_uptime_pct"],
                "mempool_pending_count": market["mempool_pending_count"],
                "single_position_pct": 0.22 + max(0.0, wave) * 0.04,
                "treasury_tvl": 820_000.0,
                "target_apy": float(pool["apy_current"]) + 1.1,
                "market_avg_apy": 7.2,
                "liquidity_drop_24h_pct": 0.18 + max(0.0, -wave) * 0.12,
            }
            yield RawSignal(
                domain=self.domain_name,
                source=pool_id,
                features={k: round(v, 4) for k, v in features.items()},
                metadata={"source": pool["source"], "network": self.client.network},
            )
            idx += 1

    def execute_action(self, action: DomainAction) -> ActionOutcome:
        started = time.perf_counter()
        action_type = action.type or action.action_id
        params = action.parameters
        tx_hash = ""
        success = True
        error = None

        try:
            if action_type == "swap":
                swap = self.client.execute_swap(
                    params.get("token_a", "CSPR"),
                    params.get("token_b", "USDC"),
                    float(params.get("amount", 250.0)),
                )
                tx_hash = self.wallets["planner-casper-001"].sign_and_submit({"type": "swap", **swap})
            elif action_type in {"stake", "vote", "rebalance", "deploy_contract"}:
                tx_hash = self.wallets["planner-casper-001"].sign_and_submit({"type": action_type, "parameters": params})
            else:
                tx_hash = self.wallets["planner-casper-001"].sign_and_submit({"type": "noop", "parameters": params})
        except Exception as exc:
            success = False
            error = str(exc)

        reward = 0.82
        if float(params.get("estimated_slippage_bps", 40)) > 100:
            reward -= 0.25
        if float(params.get("gas_price_motes", 2_500_000_000)) > 3_000_000_000:
            reward -= 0.1
        if not success:
            reward = 0.0

        return ActionOutcome(
            action_id=action.action_id,
            success=success,
            reward=max(0.0, min(1.0, reward)),
            state_delta={
                "tx_hash": tx_hash,
                "explorer_url": f"https://testnet.cspr.live/deploy/{tx_hash}",
                "mode": self.client.mode,
            },
            latency_ms=(time.perf_counter() - started) * 1000,
            error=error,
        )

    def reward(self, outcome: ActionOutcome) -> float:
        return max(0.0, min(1.0, outcome.reward))

    def available_actions(self) -> list[dict[str, Any]]:
        return [
            {
                "action_id": "swap",
                "label": "Swap",
                "parameters": {"token_a": "CSPR", "token_b": "USDC", "amount": 250.0},
                "relevant_states": ["normal", "degraded"],
                "requires_guardian": True,
            },
            {
                "action_id": "stake",
                "label": "Stake",
                "parameters": {"validator": "validator-17", "amount": 500.0},
                "relevant_states": ["normal"],
            },
            {
                "action_id": "vote",
                "label": "Governance Vote",
                "parameters": {"proposal_id": "dao-47", "direction": "yes"},
                "relevant_states": ["normal", "critical"],
                "requires_guardian": True,
            },
            {
                "action_id": "rebalance",
                "label": "Rebalance",
                "parameters": {"target_weights": {"CSPR": 0.55, "USDC": 0.25, "LP": 0.20}},
                "relevant_states": ["degraded", "recovering"],
                "requires_guardian": True,
            },
            {
                "action_id": "deploy_contract",
                "label": "Deploy Odra Contract",
                "parameters": {"contract": "agent_registry"},
                "relevant_states": ["normal"],
                "requires_guardian": True,
            },
        ]

    def health_check(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "status": "ok",
            "network": self.client.network,
            "mode": self.client.mode,
            "mcp_servers_configured": sum(1 for server in CASPER_MCP_SERVERS.values() if server.url),
            "wallet_count": len(self.wallets),
            "x402_enabled": True,
        }

    def portfolio(self) -> dict[str, Any]:
        holdings = [
            {"asset": "CSPR", "amount": 185_000, "value_usd": 462_500, "allocation_pct": 56.4},
            {"asset": "USDC", "amount": 188_000, "value_usd": 188_000, "allocation_pct": 22.9},
            {"asset": "CSPR/USDC LP", "amount": 1_940, "value_usd": 128_400, "allocation_pct": 15.7},
            {"asset": "Governance escrow", "amount": 42_000, "value_usd": 41_100, "allocation_pct": 5.0},
        ]
        return {
            "total_value_usd": sum(h["value_usd"] for h in holdings),
            "pnl_24h_pct": 1.82,
            "risk_score": 0.41,
            "holdings": holdings,
            "wallets": [wallet.public_state() for wallet in self.wallets.values()],
        }

    def yield_monitor(self) -> list[dict[str, Any]]:
        return [
            {
                "protocol": "CSPR.trade",
                "pool": "CSPR/USDC",
                "apy_current": 12.9,
                "apy_7d_avg": 11.8,
                "tvl_usd": 2_420_000,
                "slippage_bps": 42,
                "status": "eligible",
            },
            {
                "protocol": "Friendly Market",
                "pool": "CSPR/WETH",
                "apy_current": 18.4,
                "apy_7d_avg": 13.2,
                "tvl_usd": 940_000,
                "slippage_bps": 88,
                "status": "watch",
            },
            {
                "protocol": "Validator Set",
                "pool": "CSPR staking",
                "apy_current": 9.4,
                "apy_7d_avg": 9.2,
                "tvl_usd": 8_800_000,
                "slippage_bps": 0,
                "status": "eligible",
            },
        ]

    def consensus(self) -> dict[str, Any]:
        return demo_quorum_snapshot()

    def reputation(self) -> dict[str, Any]:
        return get_reputation_tracker().snapshot()

    def transactions(self) -> list[dict[str, Any]]:
        now = time.time()
        return [
            {
                "deploy_hash": "deploy-x402-5f0e9b1c2a778810",
                "type": "x402_payment",
                "status": "finalized",
                "agent_id": "planner-casper-001",
                "amount_motes": 100_000,
                "fee_motes": 2_500_000,
                "timestamp": now - 92,
                "explorer_url": "https://testnet.cspr.live/deploy/deploy-x402-5f0e9b1c2a778810",
            },
            {
                "deploy_hash": "deploy-quorum-vote-9124ac10",
                "type": "governance_vote",
                "status": "pending",
                "agent_id": "guardian-casper-001",
                "amount_motes": 0,
                "fee_motes": 2_100_000,
                "timestamp": now - 240,
                "explorer_url": "https://testnet.cspr.live/deploy/deploy-quorum-vote-9124ac10",
            },
            {
                "deploy_hash": "deploy-registry-1c22da90",
                "type": "agent_registry",
                "status": "finalized",
                "agent_id": "perceiver-casper-001",
                "amount_motes": 0,
                "fee_motes": 3_000_000,
                "timestamp": now - 680,
                "explorer_url": "https://testnet.cspr.live/deploy/deploy-registry-1c22da90",
            },
        ]

    def threats(self) -> list[dict[str, Any]]:
        return [threat.to_dict() for threat in ThreatScanner(self.client, publish_events=False).scan_cycle()]

    def dashboard(self) -> dict[str, Any]:
        latest_signal = next(self.signal_stream())
        return {
            "network": self.health_check(),
            "latest_signal": {
                "timestamp": latest_signal.timestamp,
                "source": latest_signal.source,
                "features": latest_signal.features,
            },
            "portfolio": self.portfolio(),
            "yields": self.yield_monitor(),
            "consensus": self.consensus(),
            "reputation": self.reputation(),
            "transactions": self.transactions(),
            "threats": self.threats(),
        }
