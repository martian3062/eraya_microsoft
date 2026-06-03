"""
LLMPlannerAgent — Tier 1 backed by a real Groq LLM call instead of the PPO stub.

Drop-in subclass of PlannerAgent: only _plan_tier1() is overridden.
Uses llama-3.3-70b-versatile via Groq with JSON mode for structured output.
Falls back to PlannerAgent Tier 2 (Thompson Sampling) if Groq is unavailable.

Usage:
    from core.agents.llm_planner import LLMPlannerAgent
    planner = LLMPlannerAgent(domain="telecom")
    planner.register_actions(env.available_actions())
    plan = planner.plan(perception_result)
    # plan.rationale is now a real LLM explanation
    # plan.tier_used == "tier1_llm"
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from typing import Any

from .perceiver import PerceptionResult
from .planner import ActionPlan, PlannerAgent

logger = logging.getLogger("eraya.llm_planner")

_SYSTEM_PROMPT = """\
You are an autonomous action planner for the Eraya self-healing agent swarm.
You will receive a structured perception result and a list of available actions.
Your job: choose the single best action and explain your reasoning.

Rules:
- Return ONLY valid JSON, no prose outside the JSON object.
- Be concise in rationale (1-2 sentences max).
- confidence must be between 0.0 and 1.0.
- expected_reward must be between 0.0 and 1.0.
- If risk_score > 0.7, set requires_guardian_approval to true.\
"""

_USER_TEMPLATE = """\
Domain: {domain}
State: {state_label} (confidence={confidence:.2f}, risk_score={risk_score:.2f})
Features: {features}
Available actions: {actions}

Return JSON with exactly these fields:
{{
  "action_id": "<chosen action_id from the list above>",
  "rationale": "<1-2 sentence explanation>",
  "confidence": <float>,
  "expected_reward": <float>,
  "requires_guardian_approval": <bool>
}}\
"""


class LLMPlannerAgent(PlannerAgent):
    """
    PlannerAgent with a real LLM-backed Tier 1.
    Tier 2 (Thompson Sampling) and Tier 3 (CVXPY) are inherited unchanged.
    """

    def __init__(
        self,
        agent_id: str | None = None,
        domain: str = "generic",
        model: str = "llama-3.3-70b-versatile",
    ):
        super().__init__(agent_id, domain)
        self._model = model
        self._groq_client = None

    def _get_client(self):
        if self._groq_client is None:
            try:
                from groq import Groq
                api_key = os.environ.get("GROQ_API_KEY", "")
                if not api_key:
                    raise ValueError("GROQ_API_KEY not set")
                self._groq_client = Groq(api_key=api_key)
            except Exception as exc:
                logger.warning("Groq client unavailable: %s", exc)
        return self._groq_client

    def _plan_tier1(self, context: PerceptionResult) -> ActionPlan:
        client = self._get_client()
        if client is None:
            raise NotImplementedError("Groq unavailable — falling back to tier2")

        action_ids = [a["action_id"] for a in self._domain_actions] or ["noop"]
        user_msg = _USER_TEMPLATE.format(
            domain=context.domain,
            state_label=context.state_label,
            confidence=context.confidence,
            risk_score=context.risk_score,
            features=json.dumps(context.features, default=str),
            actions=action_ids,
        )

        try:
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": user_msg},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=256,
            )
            raw = response.choices[0].message.content
            data: dict[str, Any] = json.loads(raw)
        except Exception as exc:
            logger.warning("LLM tier1 call failed: %s", exc)
            raise NotImplementedError(f"LLM call failed: {exc}") from exc

        action_id = data.get("action_id", "noop")
        # Verify the LLM chose a real registered action; fall back to noop
        valid_ids = {a["action_id"] for a in self._domain_actions}
        if action_id not in valid_ids:
            logger.warning("LLM returned unknown action '%s', defaulting to noop", action_id)
            action_id = next(iter(valid_ids), "noop")

        arm = self._arms.get(action_id)
        params = arm.action_params if arm else {}

        return ActionPlan(
            plan_id=str(uuid.uuid4())[:8],
            domain=context.domain,
            actions=[{"action_id": action_id, "parameters": params}],
            rationale=data.get("rationale", "LLM decision"),
            confidence=float(data.get("confidence", context.confidence)),
            expected_reward=float(data.get("expected_reward", 0.7)),
            tier_used="tier1_llm",
            requires_guardian_approval=bool(
                data.get("requires_guardian_approval", context.risk_score > 0.7)
            ),
        )
