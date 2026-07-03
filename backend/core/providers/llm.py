"""
LLM cascade facade - Tier-1 planning brain for the swarm.

Tries providers in order and returns the first success:
    Groq (fast) -> Kimi / Moonshot (long-context) -> local Hugging Face model

Groq and Kimi speak the OpenAI-compatible /chat/completions API, so we call them
with plain httpx. The local HF fallback uses core.agents.local_models and only
loads when the cloud providers fail or are absent. Every path is defensive: a
missing key/package/model just moves to the next provider. If none are
configured/reachable, `complete()` returns None and the caller falls back to its
own logic (e.g. the PlannerAgent's Thompson-Sampling Tier 2).
"""
from __future__ import annotations

import json
import logging

from . import config

logger = logging.getLogger("eraya.providers.llm")

# (name, base_url, api_key_setting, model_setting, default_model)
_CHAIN = [
    ("groq",        "https://api.groq.com/openai/v1", "GROQ_API_KEY",        "GROQ_MODEL",        "llama-3.3-70b-versatile"),
    ("kimi",        "https://api.moonshot.ai/v1",     "KIMI_API_KEY",        "KIMI_MODEL",        "kimi-k2-0711-preview"),
]


def _call(base_url, api_key, model, system, user, json_mode, max_tokens, timeout=30):
    import httpx
    # OpenAI/Groq require the literal word "json" somewhere in the prompt when
    # response_format is json_object - inject a hint if the caller omitted it.
    if json_mode and "json" not in (system + user).lower():
        system = f"{system}\n\nRespond with a valid JSON object."
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def complete(system: str, user: str, json_mode: bool = True, max_tokens: int = 512):
    """Return {'text','provider','model'} from the first working provider, or None."""
    for name, base_url, key_name, model_name, default_model in _CHAIN:
        api_key = config.get(key_name)
        if not api_key:
            continue
        model = config.get(model_name, default_model) or default_model
        try:
            text = _call(base_url, api_key, model, system, user, json_mode, max_tokens)
            return {"text": text, "provider": name, "model": model}
        except Exception as exc:
            logger.warning("LLM provider '%s' failed, cascading: %s", name, exc)
            continue
    local = _complete_local(system, user, json_mode, max_tokens)
    if local is not None:
        return local
    return None


def complete_json(system: str, user: str, max_tokens: int = 512):
    """Like complete(), but parses the response as JSON. Returns
    {'data','provider','model'} or None."""
    res = complete(system, user, json_mode=True, max_tokens=max_tokens)
    if not res:
        return None
    try:
        return {"data": json.loads(res["text"]), "provider": res["provider"], "model": res["model"]}
    except Exception as exc:
        logger.warning("LLM JSON parse failed (%s): %s", res.get("provider"), exc)
        return None


def available() -> list[str]:
    """Names of providers that currently have a key configured."""
    providers = [name for name, _, key_name, _, _ in _CHAIN if config.get(key_name)]
    if _local_enabled():
        providers.append("local_hf")
    return providers


def _local_enabled() -> bool:
    raw = config.get("HF_LOCAL_LLM_ENABLED", "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _complete_local(system: str, user: str, json_mode: bool, max_tokens: int):
    if not _local_enabled():
        return None
    model_key = config.get("HF_LOCAL_LLM_MODEL", "flan-t5-small")
    try:
        from core.agents.local_models import get_model
        prompt = f"{system}\n\n{user}"
        if json_mode and "json" not in prompt.lower():
            prompt += "\n\nRespond with a valid JSON object."
        model = get_model(model_key)
        old_limit = model.max_new_tokens
        model.max_new_tokens = min(max_tokens, old_limit)
        try:
            text = model.generate(prompt)
        finally:
            model.max_new_tokens = old_limit
        if text:
            return {"text": text, "provider": "local_hf", "model": model.model_id}
    except Exception as exc:
        logger.warning("Local HF LLM fallback unavailable: %s", exc)
    return None
