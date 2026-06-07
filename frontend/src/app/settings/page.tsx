"use client";
import { useState, useEffect } from "react";
import useSWR from "swr";
import {
  Settings2, Cpu, Cloud, Zap, CheckCircle2, Circle,
  HardDrive, Globe, Key, ChevronDown, ChevronUp,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useModelStore } from "@/store/model";

/* ── Types ──────────────────────────────────────────────────────── */
interface ModelMeta {
  key: string;
  model_id: string;
  display_name: string;
  params_m: number;
  size_mb: number;
  task: string;
  source: "local" | "groq";
  description: string;
  badge: string;
  quantized: boolean;
  available: boolean;
  loaded: boolean;
}

/* ── Static fallback (shown when backend is offline) ────────────── */
const STATIC_MODELS: ModelMeta[] = [
  /* Local */
  {
    key: "flan-t5-small", model_id: "google/flan-t5-small",
    display_name: "Flan-T5 Small", params_m: 80, size_mb: 308,
    task: "text2text-generation", source: "local", badge: "Seq2Seq",
    description: "Google Flan-T5 instruction-tuned. Excellent for structured prompts and planning without a GPU.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "t5-small", model_id: "t5-small",
    display_name: "T5 Small", params_m: 60, size_mb: 242,
    task: "text2text-generation", source: "local", badge: "Seq2Seq",
    description: "Google T5 Small seq2seq. Fastest local model on CPU.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "distilgpt2", model_id: "distilgpt2",
    display_name: "DistilGPT-2", params_m: 82, size_mb: 353,
    task: "text-generation", source: "local", badge: "Causal LM",
    description: "Distilled GPT-2. Tiny, fast, great for quick iteration.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "flame-3b", model_id: "microsoft/FLAME-3B",
    display_name: "FLAME 3B", params_m: 3000, size_mb: 6144,
    task: "text-generation", source: "local", badge: "Causal LM",
    description: "Microsoft FLAME — structured-reasoning and formula LM. 4-bit quant recommended.",
    quantized: true, available: true, loaded: false,
  },
  {
    key: "baby-llama", model_id: "Felladrin/BabyLlama-58M",
    display_name: "BabyLlama 58M", params_m: 58, size_mb: 220,
    task: "text-generation", source: "local", badge: "Causal LM",
    description: "Tiny Llama-architecture, 58M params. Runs on any CPU with no GPU.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "gemma-3-1b", model_id: "google/gemma-3-1b-it",
    display_name: "Gemma 3 1B-IT", params_m: 1000, size_mb: 2048,
    task: "text-generation", source: "local", badge: "Instruction",
    description: "Google Gemma 3 instruction-tuned 1B — smallest production-quality Gemma 3. Requires HF token.",
    quantized: false, available: true, loaded: false,
  },
  /* Groq */
  {
    key: "groq-llama-3.3-70b", model_id: "llama-3.3-70b-versatile",
    display_name: "LLaMA 3.3 70B", params_m: 70000, size_mb: 0,
    task: "text-generation", source: "groq", badge: "Groq API",
    description: "Meta LLaMA 3.3 70B via Groq. Primary Tier-1 planner. ~180 tok/s.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "groq-llama-3.1-8b", model_id: "llama-3.1-8b-instant",
    display_name: "LLaMA 3.1 8B Instant", params_m: 8000, size_mb: 0,
    task: "text-generation", source: "groq", badge: "Groq API",
    description: "Meta LLaMA 3.1 8B — fastest Groq model, ~750 tok/s, low-latency decisions.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "groq-mixtral-8x7b", model_id: "mixtral-8x7b-32768",
    display_name: "Mixtral 8×7B", params_m: 46700, size_mb: 0,
    task: "text-generation", source: "groq", badge: "Groq API",
    description: "Mistral MoE with 32K context. Strong multi-step reasoning.",
    quantized: false, available: true, loaded: false,
  },
  {
    key: "groq-gemma2-9b", model_id: "gemma2-9b-it",
    display_name: "Gemma 2 9B-IT", params_m: 9000, size_mb: 0,
    task: "text-generation", source: "groq", badge: "Groq API",
    description: "Google Gemma 2 9B instruction-tuned via Groq. Balanced performance.",
    quantized: false, available: true, loaded: false,
  },
];

/* ── Helpers ─────────────────────────────────────────────────────── */
function fmtParams(m: number) {
  if (m >= 1_000) return `${(m / 1000).toFixed(0)}B`;
  return `${m}M`;
}
function fmtSize(mb: number) {
  if (mb === 0) return "via API";
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb} MB`;
}

/* ── Model card ─────────────────────────────────────────────────── */
function ModelCard({
  model, active, onSelect,
}: { model: ModelMeta; active: boolean; onSelect: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const isLocal = model.source === "local";

  return (
    <div className={cn(
      "rounded-xl border transition-all duration-200 overflow-hidden",
      active
        ? "border-teal-400 dark:border-teal-600 shadow-sm shadow-teal-200/60 dark:shadow-teal-900/40"
        : "border-slate-200 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-800",
      !model.available && "opacity-50"
    )}>
      {/* Card body */}
      <div className="p-4 bg-white/70 dark:bg-white/5">
        <div className="flex items-start gap-3">
          {/* Source icon */}
          <div className={cn(
            "mt-0.5 p-1.5 rounded-lg shrink-0",
            isLocal
              ? "bg-teal-50 dark:bg-teal-900/30 text-teal-600 dark:text-teal-400"
              : "bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400"
          )}>
            {isLocal ? <Cpu size={13} /> : <Cloud size={13} />}
          </div>

          {/* Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                {model.display_name}
              </span>
              <span className={cn(
                "text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded border",
                isLocal
                  ? "text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/30 border-teal-200 dark:border-teal-800"
                  : "text-violet-700 dark:text-violet-400 bg-violet-50 dark:bg-violet-900/30 border-violet-200 dark:border-violet-800"
              )}>
                {model.badge}
              </span>
              {model.quantized && (
                <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded border text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 border-amber-200 dark:border-amber-800">
                  4-bit
                </span>
              )}
            </div>

            <div className="flex items-center gap-3 mt-1 flex-wrap">
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                {model.model_id}
              </span>
            </div>

            {/* Stats row */}
            <div className="flex items-center gap-3 mt-2">
              <Stat icon={<Zap size={10} />} value={fmtParams(model.params_m)} />
              <Stat icon={<HardDrive size={10} />} value={fmtSize(model.size_mb)} />
              <Stat icon={<Globe size={10} />} value={model.task === "text2text-generation" ? "Seq2Seq" : "Causal"} />
            </div>
          </div>

          {/* Active radio */}
          <button
            onClick={onSelect}
            disabled={!model.available}
            className="shrink-0 mt-0.5"
            title={active ? "Active model" : "Set as active"}
          >
            {active
              ? <CheckCircle2 size={18} className="text-teal-500" />
              : <Circle size={18} className="text-slate-300 dark:text-slate-600 hover:text-teal-400 transition-colors" />
            }
          </button>
        </div>

        {/* Expandable description */}
        <button
          onClick={() => setExpanded((v) => !v)}
          className="flex items-center gap-1 mt-3 text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
        >
          {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {expanded ? "Less" : "Details"}
        </button>
        {expanded && (
          <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
            {model.description}
          </p>
        )}
      </div>

      {/* Active footer */}
      {active && (
        <div className="px-4 py-1.5 bg-teal-50 dark:bg-teal-900/20 border-t border-teal-100 dark:border-teal-900/50 flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-teal-500" />
          <span className="text-[10px] text-teal-700 dark:text-teal-400 font-medium">Active — Planner Tier 1</span>
        </div>
      )}
    </div>
  );
}

function Stat({ icon, value }: { icon: React.ReactNode; value: string }) {
  return (
    <span className="flex items-center gap-1 text-[10px] text-slate-400 dark:text-slate-500">
      {icon}
      <span className="font-mono">{value}</span>
    </span>
  );
}

/* ── Connection setting row ─────────────────────────────────────── */
function Setting({ label, value, masked }: { label: string; value: string; masked?: boolean }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-teal-50 dark:border-teal-900/20 last:border-0">
      <span className="text-sm text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-xs font-mono text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-teal-900/30 border border-teal-100 dark:border-teal-800 rounded px-2 py-0.5 max-w-[240px] truncate">
        {masked ? "••••••••••••••••" : value}
      </span>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────── */
export default function SettingsPage() {
  const { activeModelKey, setActiveModel } = useModelStore();

  const { data } = useSWR<{ models: ModelMeta[] }>(
    "model-registry",
    async () => {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/agents/models/`);
      if (!res.ok) throw new Error("Backend offline");
      return res.json();
    },
    { revalidateOnFocus: false }
  );

  const models: ModelMeta[] = data?.models ?? STATIC_MODELS;
  const localModels  = models.filter((m) => m.source === "local");
  const groqModels   = models.filter((m) => m.source === "groq");
  const activeModel  = models.find((m) => m.key === activeModelKey);

  /* If persisted key doesn't match any known model, reset to default */
  useEffect(() => {
    if (models.length > 0 && !models.find((m) => m.key === activeModelKey)) {
      setActiveModel("groq-llama-3.3-70b");
    }
  }, [models, activeModelKey, setActiveModel]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">

      {/* ── Header ────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900/40 dark:to-cyan-900/20 shadow-sm">
          <Settings2 size={16} className="text-teal-600 dark:text-teal-400" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">Settings</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400">Model registry · API keys · connection config</p>
        </div>
      </div>

      {/* ── Active model banner ────────────────────────────────────── */}
      {activeModel && (
        <div className="rounded-2xl border border-teal-200 dark:border-teal-800 bg-gradient-to-r from-teal-50 to-cyan-50 dark:from-teal-900/20 dark:to-cyan-900/10 p-4 flex items-center gap-4">
          <div className={cn(
            "p-2 rounded-xl shrink-0",
            activeModel.source === "local"
              ? "bg-teal-100 dark:bg-teal-900/40 text-teal-600 dark:text-teal-400"
              : "bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400"
          )}>
            {activeModel.source === "local" ? <Cpu size={16} /> : <Cloud size={16} />}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-slate-800 dark:text-slate-100">
              {activeModel.display_name}
            </div>
            <div className="text-[10px] font-mono text-slate-400 dark:text-slate-500 mt-0.5 truncate">
              {activeModel.model_id}
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-[10px] text-slate-400 dark:text-slate-500">Active Planner Model</div>
            <div className="text-xs font-mono font-semibold text-teal-700 dark:text-teal-400 mt-0.5">
              {fmtParams(activeModel.params_m)} · {fmtSize(activeModel.size_mb)}
            </div>
          </div>
        </div>
      )}

      {/* ── Local models ──────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Cpu size={13} className="text-teal-500" />
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Local Models
          </h2>
          <span className="text-[10px] text-slate-400 dark:text-slate-500">
            — downloaded via HuggingFace, run on CPU/GPU
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {localModels.map((m) => (
            <ModelCard
              key={m.key}
              model={m}
              active={activeModelKey === m.key}
              onSelect={() => setActiveModel(m.key)}
            />
          ))}
        </div>
      </section>

      {/* ── Groq API models ───────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Cloud size={13} className="text-violet-500" />
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">
            Groq API Models
          </h2>
          <span className="flex items-center gap-1 text-[10px] text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded px-1.5 py-0.5">
            <Key size={9} />
            Key configured
          </span>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {groqModels.map((m) => (
            <ModelCard
              key={m.key}
              model={m}
              active={activeModelKey === m.key}
              onSelect={() => setActiveModel(m.key)}
            />
          ))}
        </div>
      </section>

      {/* ── Connection ────────────────────────────────────────────── */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Globe size={13} className="text-slate-400" />
          <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200">Connection</h2>
        </div>
        <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm px-5">
          <Setting label="API URL"         value={process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"} />
          <Setting label="WebSocket URL"   value={process.env.NEXT_PUBLIC_WS_URL  ?? "ws://localhost:8000"} />
          <Setting label="Groq API Key"    value="gsk_…" masked />
          <Setting label="HF Token"        value="hf_…" masked />
          <Setting label="Version"         value="0.1.0 — Microsoft Build 2026" />
        </div>
      </section>

    </div>
  );
}
