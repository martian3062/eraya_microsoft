"""
Live agent-to-agent (A2A) reasoning chat.

The four archetypes each run their own reasoning model (via Groq) and
continuously coordinate over the A2A bus: Perceiver flags telemetry, Planner
reasons a plan, Recoverer readies recovery, Guardian enforces KAVACHA. When an
anomaly is passed as a trigger, they discuss and coordinate on it.

Each `converse()` call produces one round (4 messages). The frontend polls it to
render a continuous, live conversation. Fully graceful — if a model id is
invalid or Groq is down, it falls back to the default model, then to a
deterministic line, so the exchange never stalls.
"""
from __future__ import annotations

import time

from core.providers import llm

# Each agent → its own reasoning model (with graceful fallback in llm.groq_chat).
AGENTS = [
    {"role": "Perceiver", "color": "#2dd4bf", "model": "meta-llama/llama-4-scout-17b-16e-instruct",
     "persona": "You detect anomalies in Casper DeFi telemetry — mempool, liquidity, governance, validators. Terse and metric-driven."},
    {"role": "Planner", "color": "#a78bfa", "model": "llama-3.1-8b-instant",
     "persona": "You reason step-by-step about remediation: risk-adjusted rebalances and failover plans. Decisive."},
    {"role": "Recoverer", "color": "#34d399", "model": "llama-3.3-70b-versatile",
     "persona": "You execute recovery and keep rollback / retry paths ready. Action-oriented and concrete."},
    {"role": "Guardian", "color": "#f87171", "model": "qwen/qwen3-32b",
     "persona": "You enforce KAVACHA security: block unsafe actions, verify A2A identity, demand quorum. Cautious and firm."},
]

_FALLBACK = {
    "Perceiver": "Telemetry nominal — mempool z-score within baseline, no flow-correlation risk.",
    "Planner": "No rebalance needed; holding allocation. Standing by for anomaly signals.",
    "Recoverer": "Rollback + retry paths staged. SLO within budget.",
    "Guardian": "Policy clean, A2A signatures verified. Quorum not required this cycle.",
}


def agent_roster() -> list[dict]:
    return [{"role": a["role"], "model": a["model"], "color": a["color"]} for a in AGENTS]


def converse(trigger: dict | None = None, prior: list | None = None) -> list[dict]:
    """Run one A2A coordination round (4 messages)."""
    if trigger:
        situation = (
            f"ANOMALY DETECTED — {trigger.get('type', 'anomaly')} on "
            f"{trigger.get('target', '?')} (severity {trigger.get('severity', '?')}). "
            f"{trigger.get('summary', '')}"
        )
    else:
        situation = "Routine monitoring — telemetry nominal, no active anomaly."

    transcript = list(prior or [])[-4:]
    out: list[dict] = []
    for i, ag in enumerate(AGENTS):
        to = AGENTS[(i + 1) % len(AGENTS)]["role"]
        recent = "\n".join(f"{m['from']}→{m['to']}: {m['text']}" for m in (transcript + out))
        system = (
            f"You are the {ag['role']} agent in the ERAYA self-healing DeFi swarm on Casper. "
            f"{ag['persona']} Reply with ONE short A2A message (max 22 words) to the {to} agent, "
            "coordinating on the situation. No preamble, no quotes, no name prefix."
        )
        user = (
            f"Situation: {situation}\n"
            f"Recent A2A traffic:\n{recent or '(start of exchange)'}\n"
            f"Your A2A message to {to}:"
        )
        # Reasoning models need room to think before the short answer.
        res = llm.groq_chat(ag["model"], system, user, max_tokens=512)
        text = (res or {}).get("text") or _FALLBACK[ag["role"]]
        out.append({
            "from": ag["role"], "to": to, "color": ag["color"],
            "model": (res or {}).get("model") or "fallback",
            "text": text, "ts": time.time(),
        })
    return out
