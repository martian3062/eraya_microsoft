"""
Sarvam AI facade for optional Indic-language operator features.

The current console does not depend on Sarvam; this module gives the provider a
safe runtime status hook and a tiny text-translation proxy for future UI work.
"""
from __future__ import annotations

from . import config


def enabled() -> bool:
    return bool(config.get("SARVAM_API_KEY"))


def translate(text: str, target_language_code: str = "hi-IN") -> dict | None:
    key = config.get("SARVAM_API_KEY")
    if not key or not text:
        return None
    try:
        import httpx

        resp = httpx.post(
            "https://api.sarvam.ai/translate",
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            json={
                "input": text[:1000],
                "source_language_code": "en-IN",
                "target_language_code": target_language_code,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None
