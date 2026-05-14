"use client";
import { useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useErayaStore } from "@/store";
import { AgentCard } from "@/components/agents/agent-card";
import { A2AFeed } from "@/components/agents/a2a-feed";
import { Activity, AlertTriangle, GitBranch, Zap } from "lucide-react";
import type { SwarmStatus, Incident } from "@/lib/api";

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

  const agentList = agents.length > 0 ? agents : swarm?.agents ?? [];
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
        <KPI label="Active Agents" value={agentList.length.toString()} icon={Activity} color="indigo" />
        <KPI label="Total Decisions" value={totalCalls.toLocaleString()} icon={Zap} color="blue" />
        <KPI label="Open Incidents" value={incidentList.length.toString()} icon={AlertTriangle} color={criticalCount > 0 ? "red" : "yellow"} />
        <KPI label="Avg Latency" value={`${avgLatency.toFixed(0)}ms`} icon={GitBranch} color="emerald" />
      </div>

      {/* Agent swarm grid */}
      <Section title="Agent Swarm" subtitle="4 archetypes, 3-tier cascade each">
        {agentList.length === 0 ? (
          <EmptyState message="No agents registered. Start the backend." />
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

function KPI({ label, value, icon: Icon, color }: { label: string; value: string; icon: React.ElementType; color: string }) {
  const colorMap: Record<string, string> = {
    indigo: "text-indigo-400 bg-indigo-900/20 border-indigo-800",
    blue: "text-blue-400 bg-blue-900/20 border-blue-800",
    yellow: "text-yellow-400 bg-yellow-900/20 border-yellow-800",
    red: "text-red-400 bg-red-900/20 border-red-800",
    emerald: "text-emerald-400 bg-emerald-900/20 border-emerald-800",
  };
  return (
    <div className={`rounded-xl border p-4 ${colorMap[color] ?? colorMap.indigo}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400">{label}</span>
        <Icon size={14} className="opacity-60" />
      </div>
      <div className="text-2xl font-bold font-mono">{value}</div>
    </div>
  );
}

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
      <div className="mb-4">
        <div className="text-sm font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-slate-500 mt-0.5">{subtitle}</div>}
      </div>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="text-slate-600 text-xs text-center py-8">{message}</div>;
}

function IncidentRow({ incident }: { incident: Incident }) {
  const severityColors: Record<string, string> = {
    low: "bg-slate-800 text-slate-400",
    medium: "bg-yellow-900/50 text-yellow-400",
    high: "bg-orange-900/50 text-orange-400",
    critical: "bg-red-900/50 text-red-400",
  };
  return (
    <div className="flex items-start gap-3 p-2 rounded-lg hover:bg-white/5 transition-colors">
      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium flex-shrink-0 ${severityColors[incident.severity] ?? severityColors.medium}`}>
        {incident.severity}
      </span>
      <div className="min-w-0">
        <div className="text-xs text-slate-200 truncate">{incident.title}</div>
        <div className="text-[10px] text-slate-500">{incident.domain} · {incident.status}</div>
      </div>
    </div>
  );
}
