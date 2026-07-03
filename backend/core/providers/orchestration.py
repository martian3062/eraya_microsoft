"""
n8n orchestration facade.

`notify(event, payload)` fires an inbound n8n webhook so workflows can route
Guardian vetoes to Slack/Telegram/email, schedule Perceiver scrapes, or trigger
Recoverer actions. No-op (returns False) when N8N_WEBHOOK_URL is unset.
"""
from __future__ import annotations

import logging

from . import config

logger = logging.getLogger("eraya.providers.orchestration")


def notify(event: str, payload: dict | None = None) -> bool:
    url = config.get("N8N_WEBHOOK_URL")
    if not url:
        return False
    try:
        import httpx
        headers = {"Content-Type": "application/json"}
        api_key = config.get("N8N_API_KEY")
        if api_key:
            headers["X-N8N-API-KEY"] = api_key
        httpx.post(url, headers=headers, json={"event": event, "payload": payload or {}}, timeout=10)
        return True
    except Exception as exc:
        logger.warning("n8n notify failed: %s", exc)
        return False


def enabled() -> bool:
    return bool(config.get("N8N_WEBHOOK_URL"))
