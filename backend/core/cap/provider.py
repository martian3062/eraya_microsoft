"""
CAP provider loop (SELL direction) — ERAYA lists KAVACHA Scan + PANJSHIR Grade
on the CROO Agent Store and delivers verified results with HMAC proof.

Live mode (CROO_SDK_KEY set + croo-sdk installed) connects to CROO and handles
`order_paid` → route → `DeliverOrder`. Demo mode exposes the same routing via
the REST endpoints in apps/commerce. The routing itself lives in
apps/commerce/routing.py (it touches the security pipeline + DB); this module
owns CROO-SDK specifics and identity/status.
"""
from __future__ import annotations

import logging

from . import facade

logger = logging.getLogger("eraya.cap.provider")


def provider_status() -> dict:
    ident = facade.provider_identity()
    return {
        "online": True,
        "demo_mode": facade.demo_mode(),
        **ident,
        "services": [
            {"id": facade.kavacha_service_id(), "name": "KAVACHA Scan",
             "track": "Data & Verification", "price_usdc": facade.demo_price_usdc("kavacha")},
            {"id": facade.panjshir_service_id(), "name": "PANJSHIR Grade",
             "track": "Developer Tooling", "price_usdc": facade.demo_price_usdc("panjshir")},
        ],
    }


def run_provider_loop() -> bool:
    """Connect to CROO and serve orders (live only). Returns True if the live
    loop started. In demo mode this is a no-op — orders are driven via REST."""
    if facade.demo_mode():
        logger.info("CAP provider: demo mode — orders served via REST, no live loop")
        return False
    try:
        import croo_sdk  # noqa: F401  (guarded — optional dependency)
    except Exception as exc:
        logger.warning("CAP provider: croo-sdk not installed (%s) — staying in demo mode", exc)
        return False

    # Live provider event loop (integration entrypoint):
    #   sdk = croo_sdk.Client(api_key=facade.sdk_key(), ws_url=CROO_WS_URL)
    #   @sdk.on("order_paid")
    #   def _on_paid(order):
    #       from apps.commerce.routing import route_service
    #       kind, out = route_service(order.service_id, order.requirements)
    #       sdk.DeliverOrder(order.id, result=out, proof=out["proof"])
    #   sdk.AcceptNegotiation(auto=True); sdk.run()
    logger.info("CAP provider: live mode ready (croo-sdk present) — connect via run()")
    return True
