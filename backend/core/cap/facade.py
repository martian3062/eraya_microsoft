"""
CAP config + demo-mode facade.

`demo_mode()` is True whenever CROO_SDK_KEY is unset (or CAP_DEMO_MODE forces
it). In demo mode the full Negotiate→Lock→Deliver→Clear lifecycle runs
deterministically with simulated USDC/PTS, while the KAVACHA/critic pipelines
and the HMAC proof stay 100% real.
"""
from __future__ import annotations

import os
import uuid


def _env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)


def sdk_key() -> str:
    return (_env("CROO_SDK_KEY", "") or "").strip()


def is_live() -> bool:
    return bool(sdk_key())


def demo_mode() -> bool:
    override = (_env("CAP_DEMO_MODE", "") or "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False
    return not is_live()


def kavacha_service_id() -> str:
    return _env("CROO_KAVACHA_SERVICE_ID") or "svc-kavacha-scan-demo"


def panjshir_service_id() -> str:
    return _env("CROO_PANJSHIR_SERVICE_ID") or "svc-panjshir-grade-demo"


def provider_identity() -> dict:
    return {
        "agent": "ERAYA-Guardian",
        "did": _env("CROO_AGENT_DID", "did:croo:eraya-guardian-demo"),
        "wallet": _env("CROO_AA_WALLET", "0xERAYA000000000000000000000000000000demo"),
        "network": "base",
        "api_url": _env("CROO_API_URL", "https://api.croo.network"),
    }


# ─── demo lifecycle helpers ──────────────────────────────────────────────────

def demo_order_id() -> str:
    return "ord_" + uuid.uuid4().hex[:12]


def demo_price_usdc(service: str) -> float:
    s = (service or "").lower()
    return 0.25 if ("kavacha" in s or "scan" in s) else 0.50


def demo_pts(service: str) -> int:
    return 5
