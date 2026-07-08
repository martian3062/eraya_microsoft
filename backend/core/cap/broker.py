"""
CAPBroker — a Planner-callable capability that hires external CAP agents and
composes them into ERAYA's plans. Discovery reuses the A2A bus registry plus
the CROO registry (demo listing). The actual DOGFOOD scan of the delivery is
done by the caller (apps/commerce.views) via routing.route_kavacha, so this
module stays in core/ without importing apps/.
"""
from __future__ import annotations

import logging

from . import client

logger = logging.getLogger("eraya.cap.broker")


def discover(capability: str, domain: str | None = None) -> list[dict]:
    """External agents that can fulfil a capability (A2A registry + CROO)."""
    agents: list[dict] = []
    try:
        from core.a2a.bus import get_bus
        for card in get_bus().find_agents(capability, domain=domain):
            agents.append({"agent_id": card.agent_id, "name": card.name,
                           "trust_tier": card.trust_tier, "source": "a2a"})
    except Exception as exc:
        logger.debug("A2A discovery skipped: %s", exc)
    # CROO registry (demo listing — replaced by croo-sdk discovery in live mode)
    agents.append({"agent_id": "cap:ext-marketdata-01", "name": "External Market-Data Agent",
                   "trust_tier": "medium", "source": "croo"})
    return agents


def hire(capability: str, budget_usdc: float, poison: bool = False) -> dict:
    """Run Negotiate → Pay → Get. Returns the discovery list, order, and the
    raw delivery. The caller MUST dogfood-scan delivery['payload'] before use."""
    order = client.negotiate(capability, budget_usdc)
    order = client.pay(order)
    delivery = client.get_delivery(order, poison=poison)
    return {"discovered": discover(capability), "order": order, "delivery": delivery}
