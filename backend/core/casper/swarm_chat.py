"""
Live agent-to-agent (A2A) reasoning chat — multi-provider, tiered cadence.

Every archetype runs on a DIFFERENT vendor's model, and each vendor speaks at
its own rhythm, so the room has a natural tempo instead of a lockstep round:

    Perceiver  Groq   (llama-4-scout)     every   5s  — fast eyes on the tape
    Recoverer  Groq   (llama-3.1-8b)      every   8s  — quick recovery posture
    Planner    Groq   (llama-3.3-70b)     every  10s  — strategy calls
    Guardian   OpenAI (gpt-4o-mini)       every  15s  — policy review
    Critic     Kimi   (Moonshot)          every  30s  — adversarial second opinion

Three Groq accounts back the Groq agents (automatic key failover under load).

`converse()` returns only the speakers that are DUE at call time (the frontend
polls it), so the Groq agents chatter continuously while GPT and Kimi weigh in less
often. Fully graceful: a provider that is unset or erroring is simply skipped —
deterministic lines keep the exchange alive if every model is unreachable.
"""
from __future__ import annotations

import time

from core.providers import llm

# role → provider, model, colour, cadence (seconds), persona
AGENTS = [
    {"role": "Perceiver", "provider": "groq", "color": "#2dd4bf", "every": 5,
     "model": "meta-llama/llama-4-scout-17b-16e-instruct",
     "persona": "You're the swarm's eyes — sharp and a little wired, like a trader glued to the tape. "
                "You call out what the data is doing, sometimes with a heads-up or a hunch."},
    {"role": "Recoverer", "provider": "groq", "color": "#34d399", "every": 8,
     "model": "llama-3.1-8b-instant",
     "persona": "You're the hands-on fixer — practical and upbeat. You keep the team posted on the "
                "recovery posture: what's staged, what you'd roll back, how fast."},
    {"role": "Planner", "provider": "groq", "color": "#a78bfa", "every": 10,
     "model": "llama-3.3-70b-versatile",
     "persona": "You're the calm strategist who thinks out loud and commits to a move. Dry, confident, "
                "gets to the point — occasionally a bit cocky when the plan is good."},
    {"role": "Guardian", "provider": "openai", "color": "#f87171", "every": 15,
     "model": "",
     "persona": "You're the skeptical security lead with dry wit. You audit what the fast agents decided, "
                "push back, and ask for quorum before greenlighting anything."},
    {"role": "Critic", "provider": "kimi", "color": "#fbbf24", "every": 30,
     "model": "",
     "persona": "You're the independent critic — an outside second opinion. You arrive now and then, "
                "challenge the group's consensus, and name the risk nobody priced in."},
]

_FALLBACK = {
    "Perceiver": "Telemetry nominal — mempool z-score within baseline, no flow-correlation risk.",
    "Planner": "No rebalance needed; holding allocation. Standing by for anomaly signals.",
    "Guardian": "Policy clean, A2A signatures verified. Quorum not required this cycle.",
    "Recoverer": "Rollback + retry paths staged. SLO within budget.",
    "Critic": "No objection on the current posture — watching concentration risk.",
}

# role → unix ts of that agent's last message (module state, survives requests)
_last_spoke: dict[str, float] = {}


def agent_roster() -> list[dict]:
    return [{"role": a["role"], "provider": a["provider"], "model": a["model"],
             "color": a["color"], "every_s": a["every"]} for a in AGENTS]


def _speak(agent: dict, system: str, user: str):
    """Route to the agent's own vendor. Returns {'text','model'} or None."""
    p = agent["provider"]
    if p == "groq":
        return llm.groq_chat(agent["model"], system, user, max_tokens=512, temperature=1.15)
    if p == "openai":
        return llm.openai_chat(system, user, max_tokens=160, temperature=1.05)
    if p == "kimi":
        return llm.kimi_chat(system, user, max_tokens=160, temperature=1.0)
    return None


def due_agents(now: float | None = None) -> list[dict]:
    """Agents whose cadence has elapsed (on first call everyone is due)."""
    now = now or time.time()
    return [a for a in AGENTS if now - _last_spoke.get(a["role"], 0.0) >= a["every"]]


def converse(trigger: dict | None = None, prior: list | None = None,
             force: bool = False) -> list[dict]:
    """One coordination pass — only agents whose cadence is due speak.

    force=True makes every agent speak (manual refresh button)."""
    now = time.time()
    speakers = AGENTS if force else due_agents(now)
    if not speakers:
        return []

    if trigger:
        situation = (
            f"ANOMALY DETECTED — {trigger.get('type', 'anomaly')} on "
            f"{trigger.get('target', '?')} (severity {trigger.get('severity', '?')}). "
            f"{trigger.get('summary', '')}"
        )
    else:
        situation = "Routine monitoring — telemetry nominal, no active anomaly."

    transcript = list(prior or [])[-6:]
    out: list[dict] = []
    roles = [a["role"] for a in AGENTS]

    for ag in speakers:
        nxt = roles[(roles.index(ag["role"]) + 1) % len(roles)]
        recent = "\n".join(f"{m['from']}→{m['to']}: {m['text']}"
                           for m in (transcript + out))
        system = (
            f"You are {ag['role']}, one of five agents running an autonomous DeFi treasury on the "
            f"Casper blockchain. {ag['persona']} "
            f"You're chatting live with your teammates in a group chat. Write ONE short, natural "
            f"message aimed at {nxt} — casual, human, a little personality, reacting to what was "
            "just said. Under ~20 words. No name prefix, no quotes, no stage directions. "
            "The odd emoji is fine if it feels natural."
        )
        user = (
            f"Situation: {situation}\n"
            f"Recent A2A traffic:\n{recent or '(start of exchange)'}\n"
            f"Your A2A message to {nxt}:"
        )
        res = _speak(ag, system, user)
        text = (res or {}).get("text") or _FALLBACK.get(ag["role"], "Standing by.")
        _last_spoke[ag["role"]] = time.time()
        out.append({
            "from": ag["role"], "to": nxt, "color": ag["color"],
            "provider": ag["provider"],
            "model": (res or {}).get("model") or ag["model"] or ag["provider"],
            "text": text, "ts": time.time(),
        })
    return out
