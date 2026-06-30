"""Demo-safe Casper wallet facade for ERAYA agents."""
from __future__ import annotations

import hashlib
import os
from typing import Any

from .mcp import CasperMCPClient


class AgentWallet:
    """Each ERAYA agent receives a deterministic Casper testnet account handle."""

    def __init__(self, agent_id: str, client: CasperMCPClient | None = None):
        self.agent_id = agent_id
        self.client = client or CasperMCPClient()
        env_name = f"CASPER_ACCOUNT_HASH_{agent_id.upper().replace('-', '_')}"
        self.account_hash = os.environ.get(env_name) or self._derive_demo_account(agent_id)

    @staticmethod
    def _derive_demo_account(agent_id: str) -> str:
        digest = hashlib.sha256(f"eraya-casper:{agent_id}".encode()).hexdigest()
        return f"account-hash-{digest[:64]}"

    def sign_and_submit(self, deploy: dict[str, Any]) -> str:
        signed = {
            **deploy,
            "agent_id": self.agent_id,
            "account_hash": self.account_hash,
            "signature_mode": "cspr-click" if os.environ.get("CSPR_CLICK_API_URL") else "demo-hash",
        }
        return self.client.submit_deploy(signed)

    def get_balance(self) -> int:
        return self.client.query_balance(self.account_hash)

    def public_state(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "account_hash": self.account_hash,
            "balance_motes": self.get_balance(),
            "network": self.client.network,
        }
