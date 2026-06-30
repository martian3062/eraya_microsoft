"""x402-enabled A2A bus variant for Casper agent economics."""
from __future__ import annotations

import hashlib
import time
from typing import Any

from .bus import A2ABus
from .schemas import A2AMessage


class X402PaymentGateway:
    """Demo settlement adapter. Replace with Casper x402 provider in live mode."""

    def pay(self, from_agent: str, to_agent: str, amount_motes: int, purpose: str) -> dict[str, Any]:
        payload = f"{from_agent}:{to_agent}:{amount_motes}:{purpose}:{int(time.time())}"
        tx_hash = "deploy-x402-" + hashlib.sha256(payload.encode()).hexdigest()[:18]
        return {
            "protocol": "x402",
            "from_agent": from_agent,
            "to_agent": to_agent,
            "amount_motes": amount_motes,
            "purpose": purpose,
            "settlement": "casper-testnet-demo",
            "tx_hash": tx_hash,
        }


class X402EnabledBus(A2ABus):
    """A2A bus where valuable agent services include a micropayment proof."""

    def __init__(self, backend: str = "memory", gateway: X402PaymentGateway | None = None):
        super().__init__(backend=backend)
        self.gateway = gateway or X402PaymentGateway()

    def publish(self, message: A2AMessage) -> bool:
        cost = self._price_message(message)
        if cost > 0 and message.payment_proof is None:
            message.payment_proof = self.gateway.pay(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                amount_motes=cost,
                purpose=message.message_type,
            )
        return super().publish(message)

    @staticmethod
    def _price_message(message: A2AMessage) -> int:
        prices = {
            "context.update": 0,
            "capability.query": 0,
            "capability.response": 0,
            "heartbeat": 0,
            "action.request": 100_000,
            "action.response": 0,
            "veto": 50_000,
            "consensus.propose": 75_000,
            "consensus.vote": 25_000,
            "threat.detected": 0,
        }
        return prices.get(message.message_type, 10_000)

    def stats(self) -> dict[str, Any]:
        data = super().stats()
        data["x402_enabled"] = True
        data["settlement"] = "casper-testnet-demo"
        return data
