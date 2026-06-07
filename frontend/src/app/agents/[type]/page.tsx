"use client";
import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { AgentCard } from "@/components/agents/agent-card";
import { Eye, Target, RefreshCcw, Shield } from "lucide-react";
import { useModelStore } from "@/store/model";

const ROLE_META = {
  perceiver: {
    icon: Eye,
    gradient: "from-blue-400 to-teal-400",
    iconBg: "bg-gradient-to-br from-blue-100 to-teal-100 dark:from-blue-900/40 dark:to-teal-900/30",
    title: "Perceiver Agent",
    subtitle: "Converts raw signals → structured context",
    cascade: [
      { algo: "Transformer + GNN encoder",         note: "GPU · PyTorch · torch-geometric" },
      { algo: "Kalman filter + XGBoost + HMM",     note: "CPU · filterpy · xgboost · hmmlearn" },
      { algo: "Bayesian classifier + rules",        note: "Always available · numpy only" },
    ],
  },
  planner: {
    icon: Target,
    gradient: "from-teal-400 to-cyan-400",
    iconBg: "bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900/40 dark:to-cyan-900/30",
    title: "Planner Agent",
    subtitle: "Selects actions that optimize the domain objective",
    cascade: [
      { algo: "PPO + MCTS policy",                 note: "Groq LLM · llama-3.3-70b · JSON mode" },
      { algo: "Thompson Sampling + LSTM",           note: "CPU · online bandit · no retraining" },
      { algo: "CVXPY convex optimization",          note: "Always available · ECOS solver" },
    ],
  },
  recoverer: {
    icon: RefreshCcw,
    gradient: "from-cyan-400 to-emerald-400",
    iconBg: "bg-gradient-to-br from-cyan-100 to-emerald-100 dark:from-cyan-900/40 dark:to-emerald-900/30",
    title: "Recoverer Agent",
    subtitle: "Detects degradation, executes fallback, preserves continuity",
    cascade: [
      { algo: "Monte Carlo rollout + RL replanning", note: "GPU · SB3 · PyTorch" },
      { algo: "Q-learning + exponential backoff",   note: "CPU · 100ms × 2ⁿ, cap 30s" },
      { algo: "Circuit breaker + static policy",    note: "Always available · CLOSED/OPEN/HALF_OPEN" },
    ],
  },
  guardian: {
    icon: Shield,
    gradient: "from-emerald-400 to-teal-400",
    iconBg: "bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/40 dark:to-teal-900/30",
    title: "Guardian Agent",
    subtitle: "PolicyAuditor · InjectionSentinel · AuditSigner",
    cascade: [
      { algo: "OPA + DeBERTa NLI classifier",      note: "Rego policies · transformers pipeline" },
      { algo: "Pattern matching + hard rules R001–R003", note: "13-pattern regex · always active" },
      { algo: "Passthrough + audit log",            note: "HMAC-SHA256 seal on every record" },
    ],
  },
} as const;

type Role = keyof typeof ROLE_META;

const TIER_STYLES = [
  {
    label: "Heavy (Tier 1)",
    labelColor: "text-teal-700 dark:text-teal-400",
    bar: "bg-gradient-to-r from-teal-400 to-cyan-400",
    card: "border-teal-200 dark:border-teal-800/50 bg-gradient-to-r from-teal-50 via-cyan-50 to-teal-50 dark:from-teal-900/20 dark:via-cyan-900/10 dark:to-teal-900/20",
    fallback: "text-teal-400 dark:text-teal-500",
  },
  {
    label: "Medium (Tier 2)",
    labelColor: "text-cyan-700 dark:text-cyan-400",
    bar: "bg-gradient-to-r from-cyan-400 to-sky-400",
    card: "border-cyan-200 dark:border-cyan-800/50 bg-gradient-to-r from-cyan-50 via-sky-50 to-cyan-50 dark:from-cyan-900/20 dark:via-sky-900/10 dark:to-cyan-900/20",
    fallback: "text-cyan-400 dark:text-cyan-500",
  },
  {
    label: "Light (Tier 3)",
    labelColor: "text-emerald-700 dark:text-emerald-400",
    bar: "bg-gradient-to-r from-emerald-400 to-teal-400",
    card: "border-emerald-200 dark:border-emerald-800/50 bg-gradient-to-r from-emerald-50 via-teal-50 to-emerald-50 dark:from-emerald-900/20 dark:via-teal-900/10 dark:to-emerald-900/20",
    fallback: null,
  },
];

const MODEL_LABELS: Record<string, string> = {
  "flan-t5-small":      "Flan-T5 Small · local · Seq2Seq",
  "t5-small":           "T5 Small · local · Seq2Seq",
  "distilgpt2":         "DistilGPT-2 · local · Causal",
  "flame-3b":           "FLAME 3B · local · 4-bit quant",
  "baby-llama":         "BabyLlama 58M · local · Causal",
  "gemma-3-1b":         "Gemma 3 1B-IT · local · gated",
  "groq-llama-3.3-70b": "Groq · llama-3.3-70b · JSON mode",
  "groq-llama-3.1-8b":  "Groq · llama-3.1-8b-instant",
  "groq-mixtral-8x7b":  "Groq · mixtral-8x7b-32768",
  "groq-gemma2-9b":     "Groq · gemma2-9b-it",
};

export default function AgentTypePage({ params }: { params: Promise<{ type: string }> }) {
  const { type } = use(params);
  const role = type as Role;
  const meta = ROLE_META[role] ?? ROLE_META.perceiver;
  const Icon = meta.icon;
  const activeModelKey = useModelStore((s) => s.activeModelKey);

  const { data: swarm } = useSWR("swarm-status", () => api.swarmStatus(), { refreshInterval: 5000 });
  const agents = swarm?.agents.filter((a) => a.role === role) ?? [];

  return (
    <div className="max-w-5xl mx-auto space-y-5">

      {/* ── Header card ────────────────────────────────────────────────── */}
      <div className="peacock-card flex items-center gap-4 p-5 rounded-2xl border border-teal-200 dark:border-teal-800/50 shadow-sm">
        <div className={`p-3 rounded-xl ${meta.iconBg} shadow-sm`}>
          <Icon size={22} className={`bg-gradient-to-br ${meta.gradient} bg-clip-text`} />
        </div>
        <div>
          <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">{meta.title}</h1>
          <p className="text-sm text-slate-500 dark:text-slate-400 mt-0.5">{meta.subtitle}</p>
        </div>
        <div className={`ml-auto w-2 h-10 rounded-full bg-gradient-to-b ${meta.gradient} opacity-60`} />
      </div>

      {/* ── 3-tier cascade ─────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">3-Tier Algorithm Cascade</h2>
        <div className="space-y-3">
          {meta.cascade.map((item, i) => {
            const t = TIER_STYLES[i];
            /* Planner Tier 1: override note with the active model */
            const note =
              role === "planner" && i === 0
                ? (MODEL_LABELS[activeModelKey] ?? item.note)
                : item.note;
            return (
              <div
                key={i}
                className={`relative flex items-center gap-4 rounded-xl border p-3.5 ${t.card} overflow-hidden`}
                style={{ backgroundSize: "200% 100%", animation: `peacock-wave ${7 + i}s ease infinite` }}
              >
                {/* Left accent bar */}
                <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${t.bar}`} />

                <div className="pl-3 flex items-center gap-4 w-full">
                  <span className={`text-[10px] font-mono font-semibold w-28 flex-shrink-0 ${t.labelColor}`}>
                    {t.label}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-slate-700 dark:text-slate-200">{item.algo}</div>
                    <div className="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{note}</div>
                  </div>
                  {t.fallback && (
                    <span className={`text-[10px] flex-shrink-0 ${t.fallback} opacity-70`}>
                      ↓ fallback if slow/unavailable
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Cascade flow indicator */}
        <div className="mt-4 flex items-center gap-2 text-[10px] text-slate-400 dark:text-slate-500">
          <div className="w-2 h-2 rounded-full bg-teal-400" />
          <span>Tier selection: GPU available + latency budget + signal quality → auto-cascade on failure</span>
        </div>
      </div>

      {/* ── Live instances ──────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
          Live Instances{" "}
          <span className="font-normal text-slate-400">({agents.length})</span>
        </h2>
        {agents.length === 0 ? (
          <div className="peacock-card-fast rounded-xl p-8 text-center text-xs text-teal-600 border border-teal-100">
            No {role} instances registered — start the backend to see live agents.
          </div>
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
