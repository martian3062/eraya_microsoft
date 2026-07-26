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
    ("groq-2",      "https://api.groq.com/openai/v1", "GROQ_API_KEY_2",      "GROQ_MODEL",        "llama-3.3-70b-versatile"),
    ("kimi",        "https://api.moonshot.ai/v1",     "KIMI_API_KEY",        "KIMI_MODEL",        "kimi-k2-0711-preview"),
]


def groq_keys() -> list[str]:
    """Configured Groq keys, primary first (extra accounts = failover)."""
    return [k for k in (config.get("GROQ_API_KEY"),
                        config.get("GROQ_API_KEY_2"),
                        config.get("GROQ_API_KEY_3")) if k]


def openai_chat(system: str, user: str, max_tokens: int = 160, temperature: float = 1.0,
                model: str | None = None):
    """Plain-text chat with OpenAI (GPT). Returns {'text','model'} or None."""
    key = config.get("OPENAI_API_KEY")
    if not key:
        return None
    m = model or config.get("OPENAI_MODEL", "gpt-4o-mini")
    try:
        text = _call("https://api.openai.com/v1", key, m, system, user, False,
                     max_tokens, temperature=temperature)
        text = (text or "").strip().strip('"“”').strip()
        if text:
            return {"text": text, "model": m}
    except Exception as exc:
        logger.warning("openai_chat failed: %s", exc)
    return None






# Moonshot retires model ids over time — try newest first, fall through on 404.
_KIMI_MODELS = ["kimi-k3", "kimi-k2-turbo-preview", "kimi-latest",
                "moonshot-v1-32k", "moonshot-v1-8k"]


def kimi_chat(system: str, user: str, max_tokens: int = 160, temperature: float = 1.0):
    """Plain-text chat with Kimi (Moonshot). Returns {'text','model'} or None."""
    key = config.get("KIMI_API_KEY")
    if not key:
        return None
    configured = config.get("KIMI_MODEL", "")
    candidates = ([configured] if configured else []) + _KIMI_MODELS
    for m in candidates:
        try:
            text = _call("https://api.moonshot.ai/v1", key, m, system, user, False,
                         max_tokens, temperature=temperature)
            text = (text or "").strip().strip('"“”').strip()
            if text:
                return {"text": text, "model": m}
        except Exception as exc:
            logger.warning("kimi_chat model '%s' failed: %s", m, exc)
            continue
    return None


def _call(base_url, api_key, model, system, user, json_mode, max_tokens, timeout=30, temperature=0.2):
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
        "temperature": temperature,
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


def groq_chat(model: str, system: str, user: str, max_tokens: int = 100, temperature: float = 1.2):
    """Plain-text chat with a SPECIFIC Groq model (for per-agent reasoning).
    Strips reasoning <think>…</think> tags. Falls back to the default Groq model
    if the requested one errors (bad id / unavailable). Returns {'text','model'}
    or None."""
    import re
    keys = groq_keys()
    if not keys:
        return None
    default = config.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    attempts = [(m, k) for m in ([model, default] if model != default else [default])
                for k in keys]
    for m, key in attempts:
        try:
            raw = _call("https://api.groq.com/openai/v1", key, m, system, user, False, max_tokens, temperature=temperature) or ""
            # Reasoning models (qwen3, gpt-oss) emit <think>…</think>; keep only the
            # answer after </think>. If reasoning was truncated (no close tag),
            # fall through to the default model.
            if "<think>" in raw and "</think>" not in raw:
                raise ValueError("reasoning truncated")
            text = raw.split("</think>")[-1] if "</think>" in raw else raw
            text = re.sub(r"</?think>", "", text).strip().strip('"“”').strip()
            if text:
                return {"text": text, "model": m}
        except Exception as exc:
            logger.warning("groq_chat model '%s' failed: %s", m, exc)
            continue
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
