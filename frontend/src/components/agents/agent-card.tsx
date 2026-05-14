"use client";
import { cn, statusColor, tierColor, formatMs } from "@/lib/utils";
import type { Agent } from "@/lib/api";
import { Eye, Target, RefreshCcw, Shield, Activity } from "lucide-react";

const ROLE_ICONS = {
  perceiver: Eye,
  planner: Target,
  recoverer: RefreshCcw,
  guardian: Shield,
};

const ROLE_COLORS = {
  perceiver: "border-blue-800 bg-blue-950/20",
  planner: "border-indigo-800 bg-indigo-950/20",
  recoverer: "border-amber-800 bg-amber-950/20",
  guardian: "border-emerald-800 bg-emerald-950/20",
};

interface AgentCardProps {
  agent: Agent;
  onQuarantine?: (id: number) => void;
  onLiftQuarantine?: (id: number) => void;
}

export function AgentCard({ agent, onQuarantine, onLiftQuarantine }: AgentCardProps) {
  const Icon = ROLE_ICONS[agent.role] ?? Activity;
  const isQuarantined = agent.status === "quarantined";
  const isDegraded = agent.status === "degraded";

  return (
    <div className={cn(
      "rounded-xl border p-4 flex flex-col gap-3 transition-colors",
      ROLE_COLORS[agent.role],
      isDegraded && "border-yellow-700",
      isQuarantined && "border-red-800 bg-red-950/20 opacity-75",
    )}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className={cn(
            "p-1.5 rounded-lg",
            isQuarantined ? "bg-red-900/50" : "bg-slate-800"
          )}>
            <Icon size={15} className={statusColor(agent.status)} />
          </div>
          <div>
            <div className="text-sm font-medium capitalize">{agent.role}</div>
            <div className="text-[10px] text-slate-500 font-mono">{agent.agent_id}</div>
          </div>
        </div>

        <StatusBadge status={agent.status} />
      </div>

      {/* Domain + tier */}
      <div className="flex items-center gap-3 text-[11px]">
        <span className="bg-slate-800 rounded px-1.5 py-0.5 text-slate-400">{agent.domain}</span>
        <span className={cn("font-mono font-medium", tierColor(agent.current_tier))}>
          {agent.current_tier}
        </span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Calls" value={agent.total_calls.toLocaleString()} />
        <Metric label="Avg lat" value={formatMs(agent.avg_latency_ms)} />
        <Metric label="Errors" value={String(agent.error_count)} highlight={agent.error_count > 0} />
      </div>

      {/* Actions */}
      {(onQuarantine || onLiftQuarantine) && (
        <div className="pt-1 border-t border-white/5">
          {isQuarantined ? (
            <button
              onClick={() => onLiftQuarantine?.(agent.id)}
              className="w-full text-[11px] py-1 rounded bg-emerald-900/50 text-emerald-400 hover:bg-emerald-900 transition-colors"
            >
              Lift quarantine
            </button>
          ) : (
            <button
              onClick={() => onQuarantine?.(agent.id)}
              className="w-full text-[11px] py-1 rounded bg-red-900/30 text-red-400 hover:bg-red-900/60 transition-colors"
            >
              Quarantine
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    idle: "bg-slate-800 text-slate-400",
    active: "bg-emerald-900/60 text-emerald-400",
    degraded: "bg-yellow-900/60 text-yellow-400",
    quarantined: "bg-red-900/60 text-red-400",
  };
  return (
    <span className={cn("text-[10px] px-2 py-0.5 rounded-full font-medium", colors[status] ?? colors.idle)}>
      {status}
    </span>
  );
}

function Metric({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex flex-col">
      <span className="text-[10px] text-slate-500">{label}</span>
      <span className={cn("text-xs font-mono font-medium", highlight ? "text-red-400" : "text-slate-200")}>
        {value}
      </span>
    </div>
  );
}
