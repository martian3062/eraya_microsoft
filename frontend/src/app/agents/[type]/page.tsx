"use client";
import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { AgentCard } from "@/components/agents/agent-card";
import { Eye, Target, RefreshCcw, Shield } from "lucide-react";

const ROLE_META = {
  perceiver: {
    icon: Eye,
    color: "text-blue-400",
    title: "Perceiver Agent",
    subtitle: "Converts raw signals → structured context",
    cascade: ["Transformer + GNN encoder", "Kalman filter + XGBoost + HMM", "Bayesian classifier + rules"],
  },
  planner: {
    icon: Target,
    color: "text-indigo-400",
    title: "Planner Agent",
    subtitle: "Selects actions that optimize the domain objective",
    cascade: ["PPO + MCTS policy", "Thompson Sampling + LSTM", "CVXPY convex optimization"],
  },
  recoverer: {
    icon: RefreshCcw,
    color: "text-amber-400",
    title: "Recoverer Agent",
    subtitle: "Detects degradation, executes fallback, preserves continuity",
    cascade: ["Monte Carlo rollout + RL replanning", "Q-learning + exponential backoff", "Circuit breaker + static policy"],
  },
  guardian: {
    icon: Shield,
    color: "text-emerald-400",
    title: "Guardian Agent",
    subtitle: "PolicyAuditor · InjectionSentinel · AuditSigner",
    cascade: ["OPA + DeBERTa classifier", "Pattern matching + hard rules", "Passthrough + audit log"],
  },
} as const;

type Role = keyof typeof ROLE_META;

export default function AgentTypePage({ params }: { params: Promise<{ type: string }> }) {
  const { type } = use(params);
  const role = type as Role;
  const meta = ROLE_META[role] ?? ROLE_META.perceiver;
  const Icon = meta.icon;

  const { data: swarm } = useSWR("swarm-status", () => api.swarmStatus(), { refreshInterval: 5000 });
  const agents = swarm?.agents.filter((a) => a.role === role) ?? [];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4 p-5 rounded-xl border border-[#1f2937] bg-[#111827]">
        <div className="p-3 rounded-xl bg-slate-800">
          <Icon size={22} className={meta.color} />
        </div>
        <div>
          <h1 className="text-lg font-semibold">{meta.title}</h1>
          <p className="text-sm text-slate-400 mt-0.5">{meta.subtitle}</p>
        </div>
      </div>

      {/* 3-tier cascade */}
      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
        <h2 className="text-sm font-medium mb-4">3-Tier Algorithm Cascade</h2>
        <div className="space-y-2">
          {meta.cascade.map((algo, i) => {
            const tierLabels = ["Heavy (Tier 1)", "Medium (Tier 2)", "Light (Tier 3)"];
            const tierColors = ["text-purple-400", "text-blue-400", "text-slate-400"];
            const tierBg = ["bg-purple-950/30 border-purple-900", "bg-blue-950/30 border-blue-900", "bg-slate-800/50 border-slate-700"];
            return (
              <div key={i} className={`flex items-center gap-3 rounded-lg border p-3 ${tierBg[i]}`}>
                <span className={`text-[10px] font-mono font-medium w-24 flex-shrink-0 ${tierColors[i]}`}>
                  {tierLabels[i]}
                </span>
                <span className="text-sm text-slate-300">{algo}</span>
                {i < 2 && (
                  <span className="ml-auto text-[10px] text-slate-600">↓ fallback if slow/unavailable</span>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Live instances */}
      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
        <h2 className="text-sm font-medium mb-4">
          Live Instances <span className="text-slate-500 font-normal">({agents.length})</span>
        </h2>
        {agents.length === 0 ? (
          <p className="text-slate-600 text-xs py-6 text-center">No {role} instances registered.</p>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {agents.map((a) => (
              <AgentCard
                key={a.agent_id}
                agent={a}
                onQuarantine={(id) => api.quarantineAgent(id)}
                onLiftQuarantine={(id) => api.liftQuarantine(id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
