"""
A2A protocol schemas — the contract for inter-agent communication.

Every message is typed, timestamped, and optionally signed.
GuardianAgent inspects the signature chain on every delegation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field
import uuid


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uid() -> str:
    return str(uuid.uuid4())


# ─── Agent capability declaration ─────────────────────────────────────────────

class AgentCapability(BaseModel):
    name: str
    description: str
    input_schema: str
    output_schema: str
    latency_sla_ms: int = 500


class AgentCard(BaseModel):
    """Published by each agent at startup. Used for peer discovery."""
    agent_id: str
    name: str
    role: str                               # perceiver | planner | recoverer | guardian
    version: str = "0.1.0"
    domain: str = "generic"
    capabilities: list[str] = Field(default_factory=list)
    input_schema: str = "Any"
    output_schema: str = "Any"
    trust_tier: Literal["high", "medium", "low"] = "high"
    latency_sla_ms: int = 500
    status: str = "idle"
    registered_at: datetime = Field(default_factory=_now)


# ─── Core message envelope ────────────────────────────────────────────────────

class A2AMessage(BaseModel):
    """Universal A2A message envelope — all agent communication uses this."""
    message_id: str = Field(default_factory=_uid)
    from_agent: str
    to_agent: str
    message_type: Literal[
        "context.update",
        "action.request",
        "action.response",
        "veto",
        "heartbeat",
        "capability.query",
        "capability.response",
        "quarantine",
    ]
    domain: str = "generic"
    payload: dict[str, Any] = Field(default_factory=dict)
    signature: str | None = None
    timestamp: datetime = Field(default_factory=_now)
    correlation_id: str | None = None


# ─── Task delegation ──────────────────────────────────────────────────────────

class TaskDelegation(BaseModel):
    """Perceiver → Planner delegation. Guardian audits the chain."""
    task_id: str = Field(default_factory=_uid)
    from_agent: str
    to_agent: str
    domain: str
    context: dict[str, Any]
    deadline_ms: int = 500
    requires_guardian_approval: bool = False
    signature: str | None = None
    delegated_at: datetime = Field(default_factory=_now)


class TaskReceipt(BaseModel):
    """Recipient acknowledges a task delegation."""
    task_id: str
    from_agent: str
    accepted: bool
    estimated_completion_ms: int = 200
    rejection_reason: str | None = None
    receipted_at: datetime = Field(default_factory=_now)


# ─── Guardian signals ─────────────────────────────────────────────────────────

class VetoSignal(BaseModel):
    """Guardian veto — stops an action and notifies operator."""
    veto_id: str = Field(default_factory=_uid)
    guardian_id: str
    target_agent_id: str
    vetoed_action: dict[str, Any]
    reason: str
    severity: Literal["warn", "block", "quarantine"] = "block"
    timestamp: datetime = Field(default_factory=_now)


# ─── Capability discovery ─────────────────────────────────────────────────────

class CapabilityQuery(BaseModel):
    """Find agents that can fulfill a capability."""
    query_id: str = Field(default_factory=_uid)
    requested_by: str
    required_capability: str
    domain: str | None = None
    max_latency_sla_ms: int | None = None
    trust_tier: Literal["high", "medium", "low"] | None = None
    queried_at: datetime = Field(default_factory=_now)


class CapabilityResponse(BaseModel):
    query_id: str
    matching_agents: list[AgentCard]
    responded_at: datetime = Field(default_factory=_now)
