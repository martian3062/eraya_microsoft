"""
Pexels media facade - optional imagery for the console / landing page.
Returns None when PEXELS_API_KEY is unset.
"""
from __future__ import annotations

import logging

from . import config

logger = logging.getLogger("eraya.providers.assets")


def search_image(query: str):
    """Return a large image URL for `query`, or None."""
    key = config.get("PEXELS_API_KEY")
    if not key:
        return None
    try:
        import httpx
        resp = httpx.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": key},
            params={"query": query, "per_page": 1},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if photos:
            return photos[0]["src"]["large"]
    except Exception as exc:
        logger.warning("Pexels search failed: %s", exc)
    return None
