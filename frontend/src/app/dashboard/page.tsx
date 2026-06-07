"use client";
import { useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useErayaStore } from "@/store";
import { AgentCard } from "@/components/agents/agent-card";
import { A2AFeed } from "@/components/agents/a2a-feed";
import { Activity, AlertTriangle, GitBranch, Zap } from "lucide-react";
import type { SwarmStatus, Incident } from "@/lib/api";
import { cn } from "@/lib/utils";

import type { Agent } from "@/lib/api";

const DEMO_AGENTS: Agent[] = [
  { id:1,  agent_id:"perceiver-5g-001",   name:"Perceiver · 5G",    role:"perceiver",  domain:"5g",      status:"active",   current_tier:"HEAVY",  total_calls:1284, avg_latency_ms:87,  error_count:2,  last_heartbeat: null },
  { id:2,  agent_id:"planner-5g-001",     name:"Planner · 5G",      role:"planner",    domain:"5g",      status:"active",   current_tier:"HEAVY",  total_calls:947,  avg_latency_ms:313, error_count:1,  last_heartbeat: null },
  { id:3,  agent_id:"recoverer-5g-001",   name:"Recoverer · 5G",    role:"recoverer",  domain:"5g",      status:"idle",     current_tier:"MEDIUM", total_calls:156,  avg_latency_ms:145, error_count:0,  last_heartbeat: null },
  { id:4,  agent_id:"guardian-5g-001",    name:"Guardian · 5G",     role:"guardian",   domain:"5g",      status:"active",   current_tier:"LIGHT",  total_calls:2103, avg_latency_ms:22,  error_count:0,  last_heartbeat: null },
  { id:5,  agent_id:"perceiver-cloud-001",name:"Perceiver · Cloud",  role:"perceiver",  domain:"cloud",   status:"active",   current_tier:"MEDIUM", total_calls:881,  avg_latency_ms:64,  error_count:0,  last_heartbeat: null },
  { id:6,  agent_id:"planner-cloud-001",  name:"Planner · Cloud",    role:"planner",    domain:"cloud",   status:"active",   current_tier:"HEAVY",  total_calls:732,  avg_latency_ms:290, error_count:3,  last_heartbeat: null },
  { id:7,  agent_id:"recoverer-cloud-001",name:"Recoverer · Cloud",  role:"recoverer",  domain:"cloud",   status:"degraded", current_tier:"MEDIUM", total_calls:214,  avg_latency_ms:188, error_count:7,  last_heartbeat: null },
  { id:8,  agent_id:"guardian-cloud-001", name:"Guardian · Cloud",   role:"guardian",   domain:"cloud",   status:"active",   current_tier:"LIGHT",  total_calls:1629, avg_latency_ms:19,  error_count:0,  last_heartbeat: null },
  { id:9,  agent_id:"perceiver-icu-001",  name:"Perceiver · ICU",    role:"perceiver",  domain:"icu",     status:"active",   current_tier:"HEAVY",  total_calls:2417, avg_latency_ms:92,  error_count:1,  last_heartbeat: null },
  { id:10, agent_id:"planner-icu-001",    name:"Planner · ICU",      role:"planner",    domain:"icu",     status:"active",   current_tier:"HEAVY",  total_calls:1853, avg_latency_ms:401, error_count:0,  last_heartbeat: null },
  { id:11, agent_id:"recoverer-icu-001",  name:"Recoverer · ICU",    role:"recoverer",  domain:"icu",     status:"active",   current_tier:"MEDIUM", total_calls:302,  avg_latency_ms:134, error_count:2,  last_heartbeat: null },
  { id:12, agent_id:"guardian-icu-001",   name:"Guardian · ICU",     role:"guardian",   domain:"icu",     status:"active",   current_tier:"LIGHT",  total_calls:3104, avg_latency_ms:15,  error_count:0,  last_heartbeat: null },
  { id:13, agent_id:"perceiver-net-001",  name:"Perceiver · Net",    role:"perceiver",  domain:"network", status:"active",   current_tier:"MEDIUM", total_calls:643,  avg_latency_ms:59,  error_count:0,  last_heartbeat: null },
  { id:14, agent_id:"planner-net-001",    name:"Planner · Net",      role:"planner",    domain:"network", status:"idle",     current_tier:"MEDIUM", total_calls:418,  avg_latency_ms:246, error_count:0,  last_heartbeat: null },
  { id:15, agent_id:"recoverer-net-001",  name:"Recoverer · Net",    role:"recoverer",  domain:"network", status:"active",   current_tier:"LIGHT",  total_calls:87,   avg_latency_ms:102, error_count:1,  last_heartbeat: null },
  { id:16, agent_id:"guardian-net-001",   name:"Guardian · Net",     role:"guardian",   domain:"network", status:"active",   current_tier:"LIGHT",  total_calls:971,  avg_latency_ms:19,  error_count:0,  last_heartbeat: null },
];

export default function DashboardPage() {
  const { setAgents, setOpenIncidents, agents, openIncidents } = useErayaStore();

  const { data: swarm } = useSWR<SwarmStatus>("swarm-status", () => api.swarmStatus(), {
    refreshInterval: 5000,
  });
  const { data: incidents } = useSWR<Incident[]>("open-incidents", () => api.openIncidents(), {
    refreshInterval: 10000,
  });

  useEffect(() => {
    if (swarm?.agents) setAgents(swarm.agents);
  }, [swarm, setAgents]);

  useEffect(() => {
    if (incidents) setOpenIncidents(incidents);
  }, [incidents, setOpenIncidents]);

  const liveAgents = agents.length > 0 ? agents : swarm?.agents ?? [];
  const agentList = liveAgents.length > 0 ? liveAgents : DEMO_AGENTS;
  const incidentList = openIncidents.length > 0 ? openIncidents : incidents ?? [];

  const totalCalls = agentList.reduce((s, a) => s + a.total_calls, 0);
  const criticalCount = incidentList.filter((i) => i.severity === "critical").length;
  const avgLatency = agentList.length > 0
    ? agentList.reduce((s, a) => s + a.avg_latency_ms, 0) / agentList.length
    : 0;

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* KPI row */}
      <div className="grid grid-cols-4 gap-4">
        <KPI label="Active Agents"   value={agentList.length.toString()}          icon={Activity}       color="orange" />
        <KPI label="Total Decisions" value={totalCalls.toLocaleString()}           icon={Zap}            color="blue" />
        <KPI label="Open Incidents"  value={incidentList.length.toString()}        icon={AlertTriangle}  color={criticalCount > 0 ? "red" : "amber"} />
        <KPI label="Avg Latency"     value={`${avgLatency.toFixed(0)}ms`}          icon={GitBranch}      color="emerald" />
      </div>

      {/* Agent swarm grid */}
      <Section title="Agent Swarm" subtitle="4 archetypes, 3-tier cascade each">
        {agentList.length === 0 ? (
          <EmptyState message="No agents registered." />
        ) : (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {agentList.map((agent) => (
              <AgentCard
                key={agent.agent_id}
                agent={agent}
                onQuarantine={(id) => api.quarantineAgent(id)}
                onLiftQuarantine={(id) => api.liftQuarantine(id)}
              />
            ))}
          </div>
        )}
      </Section>

      {/* Lower half */}
      <div className="grid grid-cols-2 gap-4">
        <Section title="A2A Message Feed" subtitle="Live inter-agent communication">
          <A2AFeed maxItems={40} />
        </Section>

        <Section title="Open Incidents" subtitle={`${incidentList.length} requiring attention`}>
          {incidentList.length === 0 ? (
            <EmptyState message="No open incidents." />
          ) : (
            <div className="space-y-2 max-h-80 overflow-y-auto">
              {incidentList.map((inc) => (
                <IncidentRow key={inc.id} incident={inc} />
              ))}
            </div>
          )}
        </Section>
      </div>
    </div>
  );
}

function KPI({ label, value, icon: Icon, color }: {
  label: string; value: string; icon: React.ElementType; color: string;
}) {
  const colorMap: Record<string, string> = {
    orange:  "text-orange-600 dark:text-orange-400 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/10 border-orange-200 dark:border-orange-800/50",
    blue:    "text-blue-500 dark:text-blue-400 bg-gradient-to-br from-blue-50 to-sky-50 dark:from-blue-900/20 dark:to-sky-900/10 border-blue-200 dark:border-blue-800/50",
    amber:   "text-amber-600 dark:text-amber-400 bg-gradient-to-br from-amber-50 to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/10 border-amber-200 dark:border-amber-800/50",
    red:     "text-red-500 dark:text-red-400 bg-gradient-to-br from-red-50 to-orange-50 dark:from-red-900/20 dark:to-orange-900/10 border-red-200 dark:border-red-800/50",
    emerald: "text-emerald-600 dark:text-emerald-400 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/10 border-emerald-200 dark:border-emerald-800/50",
  };
  return (
    <div className={cn("rounded-xl border p-4 shadow-sm backdrop-blur-sm", colorMap[color] ?? colorMap.orange)}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
        <Icon size={14} className="opacity-50" />
      </div>
      <div className="text-2xl font-bold font-mono text-slate-800 dark:text-slate-100">{value}</div>
    </div>
  );
}

function Section({ title, subtitle, children }: {
  title: string; subtitle?: string; children: React.ReactNode;
}) {
  return (
    <div className="rounded-xl border border-orange-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
      <div className="mb-4">
        <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</div>
        {subtitle && <div className="text-xs text-slate-400 dark:text-slate-500 mt-0.5">{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="text-slate-400 dark:text-slate-600 text-xs text-center py-8">{message}</div>;
}

function IncidentRow({ incident }: { incident: Incident }) {
  const severityColors: Record<string, string> = {
    low:      "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400",
    medium:   "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400",
    high:     "bg-orange-100 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400",
    critical: "bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400",
  };
  return (
    <div className="flex items-start gap-3 p-2 rounded-lg hover:bg-orange-50/50 dark:hover:bg-teal-900/20 transition-colors">
      <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0", severityColors[incident.severity] ?? severityColors.medium)}>
        {incident.severity}
      </span>
      <div className="min-w-0">
        <div className="text-xs text-slate-700 dark:text-slate-200 truncate">{incident.title}</div>
        <div className="text-[10px] text-slate-400 dark:text-slate-500">{incident.domain} · {incident.status}</div>
      </div>
    </div>
  );
}
