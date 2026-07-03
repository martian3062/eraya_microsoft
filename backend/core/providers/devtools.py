"""
Optional dev-time provider facades.

Zerve and Stitch are intentionally not in the request path. They are exposed as
status helpers so the live app can prove keys are configured without making
dashboard rendering depend on either service.
"""
from __future__ import annotations

from . import config


def status() -> dict:
    return {
        "zerve": bool(config.get("ZERVE_API_KEY")),
        "stitch": bool(config.get("STITCH_API_KEY")),
    }
