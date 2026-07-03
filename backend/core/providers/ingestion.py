"""
Web-ingestion facades - Perceiver signal sources.

fetch_markdown(url):
    Firecrawl (LLM-ready markdown) -> ZenRows / Bright Data (anti-bot proxy) -> plain httpx GET

extract_structured(url, query):
    TinyFish AI - natural-language structured extraction (optional).

All optional; each degrades to the next source and finally to a plain fetch.
Returns None only if every path fails.
"""
from __future__ import annotations

import logging

from . import config

logger = logging.getLogger("eraya.providers.ingestion")


def _firecrawl(url: str, timeout: int):
    key = config.get("FIRECRAWL_API_KEY")
    if not key:
        return None
    try:
        import httpx
        resp = httpx.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"url": url, "formats": ["markdown"]},
            timeout=timeout,
        )
        resp.raise_for_status()
        md = (resp.json().get("data") or {}).get("markdown")
        if md:
            return {"markdown": md, "source": "firecrawl"}
    except Exception as exc:
        logger.warning("Firecrawl failed: %s", exc)
    return None


def _zenrows(url: str, timeout: int):
    key = config.get("ZENROWS_API_KEY")
    if not key:
        return None
    try:
        import httpx
        resp = httpx.get(
            "https://api.zenrows.com/v1/",
            params={"url": url, "apikey": key, "js_render": "true"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return {"markdown": resp.text, "source": "zenrows"}
    except Exception as exc:
        logger.warning("ZenRows failed: %s", exc)
    return None


def _brightdata(url: str, timeout: int):
    key = config.get("BRIGHTDATA_API_KEY")
    if not key:
        return None
    try:
        import httpx
        resp = httpx.post(
            "https://api.brightdata.com/request",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"zone": config.get("BRIGHTDATA_ZONE", "web_unlocker"), "url": url, "format": "raw"},
            timeout=timeout,
        )
        resp.raise_for_status()
        return {"markdown": resp.text, "source": "brightdata"}
    except Exception as exc:
        logger.warning("Bright Data failed: %s", exc)
    return None


def fetch_markdown(url: str, timeout: int = 40):
    """Return {'markdown','source'} from the best available source, or None."""
    for fn in (_firecrawl, _zenrows, _brightdata):
        res = fn(url, timeout)
        if res:
            return res
    # Last resort: plain fetch (no anti-bot handling).
    try:
        import httpx
        resp = httpx.get(url, timeout=timeout, follow_redirects=True)
        resp.raise_for_status()
        return {"markdown": resp.text, "source": "plain"}
    except Exception as exc:
        logger.warning("Plain fetch failed for %s: %s", url, exc)
        return None


def extract_structured(url: str, query: str, timeout: int = 60):
    """TinyFish structured extraction. Returns parsed data dict or None."""
    key = config.get("TINYFISH_API_KEY")
    if not key:
        return None
    try:
        import httpx
        resp = httpx.post(
            "https://api.tinyfish.ai/v1/extract",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"url": url, "query": query},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("TinyFish extract failed: %s", exc)
        return None
