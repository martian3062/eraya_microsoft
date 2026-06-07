"use client";
import { useState, useEffect } from "react";
import { useHealthStore, HealthCheck } from "@/store/health";
import { cn } from "@/lib/utils";
import { HeartPulse, CheckCircle2, AlertTriangle, Zap, RefreshCw, Clock } from "lucide-react";

const DOMAINS = ["5g", "cloud", "icu", "network"] as const;

/* ── Countdown hook ──────────────────────────────────────────────── */
function useCountdown(periodSeconds: number) {
  const [remaining, setRemaining] = useState(periodSeconds);
  useEffect(() => {
    const iv = setInterval(() => {
      setRemaining((r) => (r <= 1 ? periodSeconds : r - 1));
    }, 1000);
    return () => clearInterval(iv);
  }, [periodSeconds]);
  return remaining;
}

/* ── Arc countdown ring ──────────────────────────────────────────── */
function CountdownRing({
  remaining, total, label, color,
}: { remaining: number; total: number; label: string; color: string }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const progress = (remaining / total) * circ;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-24 h-24">
        <svg width="96" height="96" viewBox="0 0 96 96" className="-rotate-90">
          <circle cx="48" cy="48" r={r} fill="none" stroke="currentColor"
            className="text-slate-200 dark:text-slate-700" strokeWidth="6" />
          <circle cx="48" cy="48" r={r} fill="none" stroke="currentColor"
            className={color} strokeWidth="6"
            strokeDasharray={`${circ}`}
            strokeDashoffset={`${circ - progress}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.9s linear" }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-xl font-bold font-mono text-slate-800 dark:text-slate-100">
            {String(remaining).padStart(2, "0")}
          </span>
          <span className="text-[9px] text-slate-400 dark:text-slate-500">sec</span>
        </div>
      </div>
      <div className="text-[11px] font-semibold text-slate-600 dark:text-slate-300 text-center">{label}</div>
    </div>
  );
}

/* ── Status badge ────────────────────────────────────────────────── */
function StatusBadge({ status }: { status: HealthCheck["status"] }) {
  const map = {
    ok:      "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800",
    warning: "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border-amber-200 dark:border-amber-800",
    healed:  "bg-teal-50 dark:bg-teal-900/20 text-teal-600 dark:text-teal-400 border-teal-200 dark:border-teal-800",
  };
  const icons = {
    ok:      <CheckCircle2 size={10} />,
    warning: <AlertTriangle size={10} />,
    healed:  <Zap size={10} />,
  };
  return (
    <span className={cn("flex items-center gap-1 text-[9px] font-semibold px-1.5 py-0.5 rounded border", map[status])}>
      {icons[status]} {status}
    </span>
  );
}

/* ── Domain health summary ───────────────────────────────────────── */
function DomainCard({ domain, checks }: { domain: string; checks: HealthCheck[] }) {
  const domChecks = checks.filter((c) => c.domain === domain);
  const last = domChecks[0];
  const healed  = domChecks.filter((c) => c.status === "healed").length;
  const warned  = domChecks.filter((c) => c.status === "warning").length;
  const ok      = domChecks.filter((c) => c.status === "ok").length;
  const overall = warned > 0 ? "warning" : healed > 0 ? "healed" : "ok";

  const borderMap = {
    ok:      "border-emerald-200 dark:border-emerald-800/50",
    warning: "border-amber-200 dark:border-amber-800/50",
    healed:  "border-teal-200 dark:border-teal-800/50",
  };

  return (
    <div className={cn("rounded-xl border p-4 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm", borderMap[overall])}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-bold uppercase tracking-widest text-slate-600 dark:text-slate-300">{domain}</span>
        <StatusBadge status={overall} />
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <div>
          <div className="text-lg font-bold font-mono text-emerald-600 dark:text-emerald-400">{ok}</div>
          <div className="text-[9px] text-slate-400">OK</div>
        </div>
        <div>
          <div className="text-lg font-bold font-mono text-amber-600 dark:text-amber-400">{warned}</div>
          <div className="text-[9px] text-slate-400">Warned</div>
        </div>
        <div>
          <div className="text-lg font-bold font-mono text-teal-600 dark:text-teal-400">{healed}</div>
          <div className="text-[9px] text-slate-400">Healed</div>
        </div>
      </div>
      {last && (
        <div className="mt-3 pt-2 border-t border-slate-100 dark:border-slate-800 text-[10px] text-slate-400 dark:text-slate-500 truncate">
          Last: {last.detail}
        </div>
      )}
    </div>
  );
}

/* ── Check row ───────────────────────────────────────────────────── */
function CheckRow({ check }: { check: HealthCheck }) {
  const ts = new Date(check.timestamp).toLocaleTimeString("en-US", {
    hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit",
  });

  return (
    <div className={cn(
      "flex items-start gap-3 px-3 py-2.5 rounded-lg transition-colors",
      check.status === "warning" ? "bg-amber-50/60 dark:bg-amber-900/10"
      : check.status === "healed" ? "bg-teal-50/60 dark:bg-teal-900/10"
      : "hover:bg-slate-50 dark:hover:bg-white/5"
    )}>
      {/* Interval pill */}
      <span className={cn(
        "text-[9px] font-mono font-bold px-1.5 py-0.5 rounded flex-shrink-0 mt-0.5",
        check.interval === "30s"
          ? "bg-blue-50 dark:bg-blue-900/20 text-blue-500"
          : "bg-violet-50 dark:bg-violet-900/20 text-violet-500"
      )}>
        {check.interval}
      </span>

      {/* Body */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-slate-700 dark:text-slate-200 font-mono">{check.checker}</span>
          <span className="text-slate-300 dark:text-slate-600 text-[10px]">→</span>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-mono">{check.target}</span>
          <span className="ml-auto flex-shrink-0">
            <StatusBadge status={check.status} />
          </span>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">{check.detail}</p>
      </div>

      {/* Time + latency */}
      <div className="text-right flex-shrink-0">
        <div className="text-[10px] font-mono text-slate-400 dark:text-slate-500">{ts}</div>
        <div className="text-[10px] font-mono text-teal-500">{check.latency_ms}ms</div>
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────── */
export default function SelfHealingPage() {
  const { checks, clearChecks } = useHealthStore();
  const next30 = useCountdown(30);
  const next60 = useCountdown(60);

  const total  = checks.length;
  const healed = checks.filter((c) => c.status === "healed").length;
  const warned = checks.filter((c) => c.status === "warning").length;
  const ok     = checks.filter((c) => c.status === "ok").length;

  return (
    <div className="max-w-5xl mx-auto space-y-5">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-emerald-100 to-teal-100 dark:from-emerald-900/40 dark:to-teal-900/20 shadow-sm">
            <HeartPulse size={15} className="text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">Self-Healing Monitor</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Agents auto-check every 30 s (ping) and 60 s (full health) · self-repair on detection
            </p>
          </div>
        </div>
        <button
          onClick={clearChecks}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-800"
        >
          <RefreshCw size={11} /> Clear log
        </button>
      </div>

      {/* ── Countdown + KPIs ────────────────────────────────────────── */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <div className="flex items-center gap-8 justify-center flex-wrap">
          {/* 30s ring */}
          <CountdownRing remaining={next30} total={30} label="Next ping (30 s)" color="text-blue-400" />
          {/* 60s ring */}
          <CountdownRing remaining={next60} total={60} label="Next health check (60 s)" color="text-violet-400" />

          {/* Divider */}
          <div className="h-20 w-px bg-teal-100 dark:bg-teal-900/40 hidden sm:block" />

          {/* Stats */}
          <div className="grid grid-cols-2 gap-x-8 gap-y-3">
            <Stat label="Total checks" value={total} color="text-slate-600 dark:text-slate-300" />
            <Stat label="Self-healed"  value={healed} color="text-teal-600 dark:text-teal-400" />
            <Stat label="Warnings"     value={warned} color="text-amber-600 dark:text-amber-400" />
            <Stat label="Nominal"      value={ok}     color="text-emerald-600 dark:text-emerald-400" />
          </div>

          {/* Live indicator */}
          <div className="flex flex-col items-center gap-1.5">
            <div className="w-3 h-3 rounded-full bg-emerald-400 shadow-lg shadow-emerald-300/60 animate-pulse" />
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-medium">Running</span>
          </div>
        </div>
      </div>

      {/* ── How it works ────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3 flex items-center gap-2">
          <Clock size={13} className="text-teal-500" /> Check Schedule
        </h2>
        <div className="grid grid-cols-2 gap-4 text-xs text-slate-500 dark:text-slate-400">
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-500 flex-shrink-0">30s</span>
              <span><strong className="text-slate-700 dark:text-slate-200">Ping</strong> — Guardian → Planner heartbeat. Checks tier status and latency. Rotates across domains.</span>
            </div>
            <div className="flex items-start gap-2">
              <span className="mt-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded bg-violet-50 dark:bg-violet-900/20 text-violet-500 flex-shrink-0">60s</span>
              <span><strong className="text-slate-700 dark:text-slate-200">Full health</strong> — Guardian → Perceiver + Planner + Recoverer capability query. On warning: auto-trigger Recoverer to downgrade tier or reroute.</span>
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-start gap-2">
              <Zap size={11} className="text-teal-500 flex-shrink-0 mt-0.5" />
              <span><strong className="text-slate-700 dark:text-slate-200">Self-heal</strong> — When latency exceeds budget, Recoverer demotes the agent to a lower tier, restores nominal state, and logs an HMAC-sealed audit event.</span>
            </div>
            <div className="flex items-start gap-2">
              <RefreshCw size={11} className="text-slate-400 flex-shrink-0 mt-0.5" />
              <span>All check messages appear live in the <strong className="text-slate-700 dark:text-slate-200">A2A Chat</strong> feed as they fire.</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Domain health grid ──────────────────────────────────────── */}
      <div>
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">Domain Health</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {DOMAINS.map((d) => (
            <DomainCard key={d} domain={d} checks={checks} />
          ))}
        </div>
      </div>

      {/* ── Check log ───────────────────────────────────────────────── */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <h2 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">
          Check Log <span className="font-normal text-slate-400">({total})</span>
        </h2>
        {checks.length === 0 ? (
          <div className="text-center py-10 text-xs text-slate-400 dark:text-slate-600">
            Waiting for first check… (fires ~3 s after page load)
          </div>
        ) : (
          <div className="space-y-0.5 max-h-96 overflow-y-auto">
            {checks.map((c) => (
              <CheckRow key={c.id} check={c} />
            ))}
          </div>
        )}
      </div>

    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className={cn("text-2xl font-bold font-mono", color)}>{value}</div>
      <div className="text-[10px] text-slate-400 dark:text-slate-500">{label}</div>
    </div>
  );
}
