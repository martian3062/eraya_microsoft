"""
Central config accessor for provider facades.

Reads a key from Django's ERAYA settings dict first, then falls back to the raw
environment. Never raises - returns the default if Django isn't configured yet.
Keys live in backend/.env (git-ignored) and are never committed.
"""
from __future__ import annotations

import os


def get(key: str, default: str = "") -> str:
    try:
        from django.conf import settings
        d = getattr(settings, "ERAYA", {}) or {}
        val = d.get(key)
        if val not in (None, ""):
            return val
    except Exception:
        pass
    return os.environ.get(key, default)


def has(key: str) -> bool:
    return bool(get(key))
