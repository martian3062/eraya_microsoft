const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  // Agents
  swarmStatus: () => apiFetch<SwarmStatus>("/api/agents/instances/swarm_status/"),
  agents: () => apiFetch<PagedResponse<Agent>>("/api/agents/instances/"),
  decisions: (domain?: string) =>
    apiFetch<PagedResponse<Decision>>(`/api/agents/decisions/${domain ? `?domain=${domain}` : ""}`),
  a2aMessages: () => apiFetch<PagedResponse<A2AMsg>>("/api/agents/messages/"),
  quarantineAgent: (id: number) =>
    apiFetch(`/api/agents/instances/${id}/quarantine/`, { method: "POST" }),
  liftQuarantine: (id: number) =>
    apiFetch(`/api/agents/instances/${id}/lift_quarantine/`, { method: "POST" }),

  // Domains
  domains: () => apiFetch<{ domains: DomainInfo[] }>("/api/domains/"),
  domainStatus: (name: string) => apiFetch<DomainHealth>(`/api/domains/${name}/status/`),
  domainSignals: (name: string) => apiFetch<{ signals: Signal[] }>(`/api/domains/${name}/signals/`),

  // Incidents
  incidents: () => apiFetch<PagedResponse<Incident>>("/api/incidents/"),
  openIncidents: () => apiFetch<Incident[]>("/api/incidents/open/"),
  resolveIncident: (id: number, root_cause?: string) =>
    apiFetch(`/api/incidents/${id}/resolve/`, { method: "POST", body: JSON.stringify({ root_cause }) }),

  // Audit
  auditLog: () => apiFetch<PagedResponse<AuditEntry>>("/api/audit/"),

  // KAVACHA security simulation (Feature A + B)
  attackSim: (domain: string, payload?: string) =>
    apiFetch<AttackSimResult>("/api/v1/security/attack-sim/", {
      method: "POST",
      body: JSON.stringify({ domain, payload }),
    }),
  spoofSim: (valid?: boolean, claimed_agent_id?: string, target_agent_id?: string) =>
    apiFetch<SpoofSimResult>("/api/v1/security/spoof-sim/", {
      method: "POST",
      body: JSON.stringify({ valid, claimed_agent_id, target_agent_id }),
    }),
};

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Agent {
  id: number;
  agent_id: string;
  name: string;
  role: "perceiver" | "planner" | "recoverer" | "guardian";
  domain: string;
  status: "idle" | "active" | "degraded" | "quarantined";
  current_tier: "HEAVY" | "MEDIUM" | "LIGHT";
  total_calls: number;
  avg_latency_ms: number;
  error_count: number;
  last_heartbeat: string | null;
}

export interface SwarmStatus {
  agents: Agent[];
  a2a_bus: { backend: string; registered_agents: number; subscribed_agents: number };
  registry: Record<string, unknown>;
}

export interface Decision {
  id: number;
  decision_id: string;
  domain: string;
  perceiver_id: string;
  planner_id: string;
  guardian_approved: boolean;
  action_plan: Record<string, unknown>;
  confidence: number;
  tier_used: string;
  latency_ms: number;
  created_at: string;
}

export interface A2AMsg {
  id: number;
  message_id: string;
  from_agent: string;
  to_agent: string;
  message_type: string;
  domain: string;
  payload: Record<string, unknown>;
  timestamp: string;
}

export interface Incident {
  id: number;
  incident_id: string;
  title: string;
  domain: string;
  severity: "low" | "medium" | "high" | "critical";
  status: "open" | "investigating" | "mitigating" | "resolved";
  description: string;
  detected_at: string;
  resolved_at: string | null;
}

export interface AuditEntry {
  id: number;
  record_id: string;
  agent_id: string;
  domain: string;
  verdict: "approve" | "warn" | "block" | "quarantine";
  violations: unknown[];
  timestamp: string;
}

export interface DomainInfo { name: string; status: string }
export interface DomainHealth { domain: string; status: string; [key: string]: unknown }
export interface Signal { timestamp: number; source: string; features: Record<string, number> }
export interface PagedResponse<T> { count: number; results: T[] }

// KAVACHA security types
export interface TimelineStep {
  step: string;
  ok: boolean;
  detail: string;
  score?: number;
}
export interface AttackSimResult {
  verdict: "BLOCKED";
  injection_score: number;
  rule_fired: string;
  audit_id: string;
  timeline: TimelineStep[];
}
export interface SpoofSimResult {
  accepted: boolean;
  reason: string;
  claimed_agent_id: string;
  expected_signature: string;
  presented_signature: string;
  audit_id: string;
}
