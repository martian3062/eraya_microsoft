"use client";
import { cn, statusColor, tierColor, formatMs } from "@/lib/utils";
import type { Agent } from "@/lib/api";
import { Eye, Target, RefreshCcw, Shield, Activity } from "lucide-react";

const ROLE_ICONS = {
  perceiver: Eye,
  planner:   Target,
  recoverer: RefreshCcw,
  guardian:  Shield,
};

const ROLE_COLORS: Record<string, string> = {
  perceiver: "border-blue-200   dark:border-blue-800/50   bg-gradient-to-br from-blue-50   to-sky-50   dark:from-blue-900/20   dark:to-sky-900/10",
  planner:   "border-orange-200 dark:border-orange-800/50 bg-gradient-to-br from-orange-50 to-amber-50 dark:from-orange-900/20 dark:to-amber-900/10",
  recoverer: "border-amber-200  dark:border-amber-800/50  bg-gradient-to-br from-amber-50  to-yellow-50 dark:from-amber-900/20 dark:to-yellow-900/10",
  guardian:  "border-emerald-200 dark:border-emerald-800/50 bg-gradient-to-br from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/10",
};

interface AgentCardProps {
  agent: Agent;
  onQuarantine?: (id: number) => void;
  onLiftQuarantine?: (id: number) => void;
}

export function AgentCard({ agent, onQuarantine, onLiftQuarantine }: AgentCardProps) {
  const Icon = ROLE_ICONS[agent.role as keyof typeof ROLE_ICONS] ?? Activity;
  const isQuarantined = agent.status === "quarantined";
  const isDegraded    = agent.status === "degraded";

  return (
    <div className={cn(
      "rounded-xl border p-4 flex flex-col gap-3 transition-colors shadow-sm backdrop-blur-sm",
      ROLE_COLORS[agent.role] ?? ROLE_COLORS.perceiver,
      isDegraded    && "border-amber-300 dark:border-amber-700",
      isQuarantined && "border-red-300 dark:border-red-700 bg-red-50 dark:bg-red-900/20 opacity-75",
    )}>
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className={cn(
            "p-1.5 rounded-lg shadow-sm",
            isQuarantined ? "bg-red-100 dark:bg-red-900/30" : "bg-white/80 dark:bg-white/10"
          )}>
            <Icon size={15} className={statusColor(agent.status)} />
          </div>
          <div>
            <div className="text-sm font-medium capitalize text-slate-800 dark:text-slate-100">{agent.role}</div>
            <div className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">{agent.agent_id}</div>
          </div>
        </div>
        <StatusBadge status={agent.status} />
      </div>

      {/* Domain + tier */}
      <div className="flex items-center gap-3 text-[11px]">
        <span className="bg-white/80 dark:bg-white/10 border border-slate-200 dark:border-slate-700 rounded px-1.5 py-0.5 text-slate-500 dark:text-slate-400">
          {agent.domain}
        </span>
        <span className={cn("font-mono font-medium", tierColor(agent.current_tier))}>
          {agent.current_tier}
        </span>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2">
        <Metric label="Calls"   value={agent.total_calls.toLocaleString()} />
        <Metric label="Avg lat" value={formatMs(agent.avg_latency_ms)} />
        <Metric label="Errors"  value={String(agent.error_count)} highlight={agent.error_count > 0} />
      </div>

      {/* Actions */}
      {(onQuarantine || onLiftQuarantine) && (
        <div className="pt-1 border-t border-white/60 dark:border-white/10">
          {isQuarantined ? (
            <button
              onClick={() => onLiftQuarantine?.(agent.id)}
              className="w-full text-[11px] py-1 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-200 dark:hover:bg-emerald-900/50 transition-colors"
            >
              Lift quarantine
            </button>
          ) : (
            <button
              onClick={() => onQuarantine?.(agent.id)}
              className="w-full text-[11px] py-1 rounded bg-red-50 dark:bg-red-900/20 text-red-500 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors"
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
    idle:        "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400",
    active:      "bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400",
    degraded:    "bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400",
    quarantined: "bg-red-100 dark:bg-red-900/30 text-red-500 dark:text-red-400",
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
      <span className="text-[10px] text-slate-400 dark:text-slate-500">{label}</span>
      <span className={cn("text-xs font-mono font-medium", highlight ? "text-red-500 dark:text-red-400" : "text-slate-700 dark:text-slate-200")}>
        {value}
      </span>
    </div>
  );
}
