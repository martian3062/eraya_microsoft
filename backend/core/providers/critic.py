"""
Critic agent — LLM-as-judge adversarial review of a proposed action.

Before the swarm executes a high-stakes move (e.g. a DeFi treasury rebalance),
an independent Critic reviews the Planner's proposal and returns an
APPROVE / REVISE / REJECT verdict with specific risks. This is the "agents that
disagree and review" half of the thesis, made concrete.

Uses the existing LLM cascade (Groq -> Kimi -> local HF). If no LLM is
reachable, falls back to a deterministic risk-threshold heuristic so the
review always returns something sane. Never raises.
"""
from __future__ import annotations

import json
import logging

from . import llm

logger = logging.getLogger("eraya.providers.critic")

_SYSTEM = (
    "You are the Critic agent in the ERAYA self-healing DeFi treasury swarm. "
    "You independently and skeptically review a proposed action from the Planner "
    "BEFORE the swarm executes it on Casper. Focus on capital risk, reversibility, "
    "liquidity/slippage, governance and security. Be specific and concise."
)


def review(action: dict, context: dict) -> dict:
    """Return an independent verdict on a proposed action.

    Shape: {verdict, risk_score, risks[], recommendation, confidence, provider}
    """
    user = (
        "Review this proposed action and return ONLY JSON.\n"
        f"Proposed action: {json.dumps(action, default=str)}\n"
        f"Context / signals: {json.dumps(context, default=str)}\n"
        'JSON schema: {"verdict":"APPROVE|REVISE|REJECT",'
        '"risk_score":<0.0-1.0>,"risks":["short risk", "..."],'
        '"recommendation":"one sentence","confidence":<0.0-1.0>}'
    )
    res = llm.complete_json(_SYSTEM, user, max_tokens=400)
    if res is None:
        return _heuristic(context)
    data = res["data"]
    # Normalise / guard the fields.
    verdict = str(data.get("verdict", "REVISE")).upper()
    if verdict not in ("APPROVE", "REVISE", "REJECT"):
        verdict = "REVISE"
    return {
        "verdict": verdict,
        "risk_score": float(data.get("risk_score", context.get("risk_score", 0.5))),
        "risks": list(data.get("risks", []))[:5] or ["No specific risks identified."],
        "recommendation": str(data.get("recommendation", "Proceed with guardian audit.")),
        "confidence": float(data.get("confidence", 0.7)),
        "provider": res["provider"],
    }


def _heuristic(context: dict) -> dict:
    rs = float(context.get("risk_score", 0.5))
    if rs > 0.85:
        verdict, rec = "REJECT", "Escalate to swarm quorum; do not auto-execute."
    elif rs > 0.6:
        verdict, rec = "REVISE", "Require guardian approval and tighter slippage bounds."
    else:
        verdict, rec = "APPROVE", "Proceed with guardian audit."
    return {
        "verdict": verdict,
        "risk_score": rs,
        "risks": ["LLM unavailable — deterministic risk-threshold review."],
        "recommendation": rec,
        "confidence": 0.5,
        "provider": "heuristic",
    }
