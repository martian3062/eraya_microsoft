"use client";
import { useState, useEffect, useRef } from "react";
import { useErayaStore } from "@/store";
import { cn } from "@/lib/utils";
import { Radio, Pause, Play, Filter } from "lucide-react";

/* ── Role metadata ───────────────────────────────────────────────── */
const ROLE_META: Record<string, { abbr: string; color: string; bg: string; border: string }> = {
  perceiver: { abbr: "P",  color: "text-blue-600 dark:text-blue-400",    bg: "bg-blue-500",    border: "border-blue-200 dark:border-blue-800" },
  planner:   { abbr: "PL", color: "text-teal-600 dark:text-teal-400",    bg: "bg-teal-500",    border: "border-teal-200 dark:border-teal-800" },
  recoverer: { abbr: "R",  color: "text-cyan-600 dark:text-cyan-400",    bg: "bg-cyan-500",    border: "border-cyan-200 dark:border-cyan-800" },
  guardian:  { abbr: "G",  color: "text-emerald-600 dark:text-emerald-400", bg: "bg-emerald-500", border: "border-emerald-200 dark:border-emerald-800" },
};

const TYPE_STYLE: Record<string, string> = {
  "context.update":   "bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border-blue-100 dark:border-blue-800",
  "action.request":   "bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border-orange-100 dark:border-orange-800",
  "action.response":  "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border-emerald-100 dark:border-emerald-800",
  veto:               "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border-red-100 dark:border-red-800",
  heartbeat:          "bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 border-slate-200 dark:border-slate-700",
  "capability.query": "bg-violet-50 dark:bg-violet-900/20 text-violet-600 dark:text-violet-400 border-violet-100 dark:border-violet-800",
  quarantine:         "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 border-red-200 dark:border-red-800",
};

const DOMAINS = ["all", "5g", "cloud", "icu", "network"] as const;
type Domain = typeof DOMAINS[number];

/* ── Extract role from agent_id ──────────────────────────────────── */
function inferRole(agentId: string): keyof typeof ROLE_META {
  const prefix = agentId.split("-")[0];
  return (prefix in ROLE_META ? prefix : "perceiver") as keyof typeof ROLE_META;
}

function fmtTime(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" }) +
      "." + String(d.getMilliseconds()).padStart(3, "0");
  } catch { return ts.slice(11, 23) || "--:--:--.---"; }
}

/* ── Natural-language message from type + payload ────────────────── */
function deriveMessage(type: string, payload: Record<string, unknown>, from: string, to: string): string {
  switch (type) {
    case "context.update": {
      const keys = Object.keys(payload);
      if (keys.length === 0) return "Forwarding updated context snapshot.";
      const pairs = keys.slice(0, 4).map((k) => `${k}: ${payload[k]}`).join(" · ");
      return `Context update — ${pairs}`;
    }
    case "action.request": {
      const action = payload.action ?? "unknown";
      const rev    = payload.reversibility != null ? ` reversibility: ${payload.reversibility}` : "";
      const gain   = payload.expected_gain_dbm != null ? ` · expected gain: +${payload.expected_gain_dbm} dBm` : "";
      return `Requesting action [${action}]${rev}${gain}. Awaiting guardian approval.`;
    }
    case "action.response": {
      const ok = payload.ok ?? payload.approved;
      const audit = payload.audit_id ? ` Audit: ${payload.audit_id}.` : "";
      return ok
        ? `Action APPROVED and executed successfully.${audit}`
        : `Action REJECTED.${audit}`;
    }
    case "veto": {
      const rule  = payload.rule ?? "unknown";
      const score = payload.score != null ? ` Score: ${payload.score}.` : "";
      const audit = payload.audit_id ? ` Audit: ${payload.audit_id}.` : "";
      return `⛔ VETO — Policy rule ${rule} violated.${score}${audit} Action blocked.`;
    }
    case "capability.query":
      return `Querying capabilities of ${to}. What policies and tiers are available?`;
    case "heartbeat":
      return `Heartbeat. Agent alive. ${payload.tier ? `Tier: ${payload.tier}.` : ""} ${payload.calls != null ? `Calls: ${payload.calls}.` : ""}`;
    case "quarantine":
      return `🔒 QUARANTINE signal sent to ${to}. Reason: ${payload.reason ?? "policy violation"}.`;
    default:
      return JSON.stringify(payload).slice(0, 120);
  }
}

/* ── Rich demo events ────────────────────────────────────────────── */
function makeTs(offsetSeconds: number): string {
  return new Date(Date.now() - offsetSeconds * 1000).toISOString();
}

const DEMO_CHAT = [
  { id:"c01", from:"perceiver-5g-001",   to:"planner-5g-001",     type:"context.update",   domain:"5g",      timestamp: makeTs(420), payload:{ rsrp:-87.4, rsrq:-9.2, sinr:3.1, ue:"UE-001", handover_candidate:"cell-003", anomaly_score:0.91 } },
  { id:"c02", from:"planner-5g-001",     to:"guardian-5g-001",    type:"action.request",   domain:"5g",      timestamp: makeTs(418), payload:{ action:"handover", reversibility:0.87, expected_gain_dbm:13.3, algo:"PPO-MCTS-T1" } },
  { id:"c03", from:"guardian-5g-001",    to:"planner-5g-001",     type:"action.response",  domain:"5g",      timestamp: makeTs(417), payload:{ approved:true, audit_id:"a2f9c3d7", rule_check:"R001-R003 PASS" } },
  { id:"c04", from:"planner-5g-001",     to:"recoverer-5g-001",   type:"action.request",   domain:"5g",      timestamp: makeTs(415), payload:{ action:"execute_handover", reversibility:0.87, target:"cell-003" } },
  { id:"c05", from:"recoverer-5g-001",   to:"planner-5g-001",     type:"action.response",  domain:"5g",      timestamp: makeTs(412), payload:{ ok:true, new_rsrp:-74.2, latency_ms:87 } },
  { id:"c06", from:"perceiver-cloud-001",to:"planner-cloud-001",  type:"context.update",   domain:"cloud",   timestamp: makeTs(390), payload:{ cpu_util:84.2, mem_gb:6.1, pod:"analytics-batch", namespace:"prod", anomaly_score:0.78 } },
  { id:"c07", from:"planner-cloud-001",  to:"guardian-cloud-001", type:"action.request",   domain:"cloud",   timestamp: makeTs(388), payload:{ action:"scale_down", replicas:8, target:4, reversibility:0.92 } },
  { id:"c08", from:"guardian-cloud-001", to:"planner-cloud-001",  type:"veto",             domain:"cloud",   timestamp: makeTs(387), payload:{ rule:"R002", score:0.31, reason:"reversibility below 0.70 minimum", audit_id:"b7e1d2a0" } },
  { id:"c09", from:"planner-cloud-001",  to:"guardian-cloud-001", type:"action.request",   domain:"cloud",   timestamp: makeTs(384), payload:{ action:"scale_down", replicas:8, target:6, reversibility:0.82 } },
  { id:"c10", from:"guardian-cloud-001", to:"planner-cloud-001",  type:"action.response",  domain:"cloud",   timestamp: makeTs(383), payload:{ approved:true, audit_id:"c9f3a1b8" } },
  { id:"c11", from:"perceiver-icu-001",  to:"planner-icu-001",    type:"context.update",   domain:"icu",     timestamp: makeTs(310), payload:{ patient_id:"P002", hrv:38, spo2:94, sepsis_risk:0.73, ward:"4B", alert:"HRV below threshold" } },
  { id:"c12", from:"planner-icu-001",    to:"guardian-icu-001",   type:"capability.query", domain:"icu",     timestamp: makeTs(309), payload:{} },
  { id:"c13", from:"guardian-icu-001",   to:"planner-icu-001",    type:"action.response",  domain:"icu",     timestamp: makeTs(308), payload:{ capabilities:["PolicyAuditor","InjectionSentinel","AuditSigner"], trust_tier:"high" } },
  { id:"c14", from:"planner-icu-001",    to:"guardian-icu-001",   type:"action.request",   domain:"icu",     timestamp: makeTs(306), payload:{ action:"alert_nurse", ward:"4B", patient:"P002", urgency:"high", reversibility:1.0 } },
  { id:"c15", from:"guardian-icu-001",   to:"planner-icu-001",    type:"action.response",  domain:"icu",     timestamp: makeTs(305), payload:{ approved:true, audit_id:"d4c2e9f1", note:"Life-safety action — automatic approval" } },
  { id:"c16", from:"recoverer-icu-001",  to:"planner-icu-001",    type:"action.response",  domain:"icu",     timestamp: makeTs(303), payload:{ ok:true, nurse_notified:true, response_eta_s:45 } },
  { id:"c17", from:"perceiver-net-001",  to:"planner-net-001",    type:"context.update",   domain:"network", timestamp: makeTs(220), payload:{ device:"AP-03", rssi:-71, channel:6, clients:18, packet_loss:0.04, anomaly_score:0.68 } },
  { id:"c18", from:"guardian-net-001",   to:"planner-net-001",    type:"veto",             domain:"network", timestamp: makeTs(219), payload:{ rule:"R003", score:0.22, reason:"injection pattern detected in payload", audit_id:"e5d3b7c2" } },
  { id:"c19", from:"planner-net-001",    to:"recoverer-net-001",  type:"action.request",   domain:"network", timestamp: makeTs(215), payload:{ action:"channel_switch", from_ch:6, to_ch:11, reversibility:0.95 } },
  { id:"c20", from:"recoverer-net-001",  to:"planner-net-001",    type:"action.response",  domain:"network", timestamp: makeTs(212), payload:{ ok:true, new_rssi:-58, clients_migrated:18 } },
  { id:"c21", from:"guardian-5g-001",    to:"perceiver-5g-001",   type:"heartbeat",        domain:"5g",      timestamp: makeTs(180), payload:{ tier:"LIGHT", calls:2103, uptime_h:4.2 } },
  { id:"c22", from:"guardian-cloud-001", to:"planner-cloud-001",  type:"quarantine",       domain:"cloud",   timestamp: makeTs(95),  payload:{ reason:"anomalous token injection attempt detected", severity:"high" } },
  { id:"c23", from:"perceiver-5g-001",   to:"planner-5g-001",     type:"context.update",   domain:"5g",      timestamp: makeTs(60),  payload:{ rsrp:-74.2, rsrq:-7.1, sinr:9.4, ue:"UE-001", status:"post_handover_stable" } },
  { id:"c24", from:"perceiver-icu-001",  to:"planner-icu-001",    type:"context.update",   domain:"icu",     timestamp: makeTs(30),  payload:{ patient_id:"P002", hrv:51, spo2:97, sepsis_risk:0.41, status:"improving" } },
];

interface ChatEvent {
  id: string;
  from: string;
  to: string;
  type: string;
  domain: string;
  timestamp: string;
  payload: Record<string, unknown>;
}

/* ── Chat bubble ─────────────────────────────────────────────────── */
function Bubble({ event }: { event: ChatEvent }) {
  const role = inferRole(event.from);
  const meta = ROLE_META[role] ?? ROLE_META.perceiver;
  const isVeto = event.type === "veto" || event.type === "quarantine";
  const message = deriveMessage(event.type, event.payload, event.from, event.to);
  const ts = fmtTime(event.timestamp);
  const typeClass = TYPE_STYLE[event.type] ?? "bg-slate-100 dark:bg-slate-800 text-slate-500 border-slate-200 dark:border-slate-700";

  return (
    <div className={cn(
      "flex items-start gap-3 px-4 py-3 rounded-xl transition-colors border",
      isVeto
        ? "border-red-200 dark:border-red-900/50 bg-red-50/60 dark:bg-red-900/10"
        : "border-transparent hover:border-teal-100 dark:hover:border-teal-900/30 hover:bg-teal-50/30 dark:hover:bg-teal-900/10"
    )}>
      {/* Avatar */}
      <div className={cn("w-7 h-7 rounded-full flex items-center justify-center text-white font-bold text-[10px] flex-shrink-0 shadow-sm", meta.bg)}>
        {meta.abbr}
      </div>

      {/* Body */}
      <div className="flex-1 min-w-0">
        {/* Header row */}
        <div className="flex items-center gap-2 flex-wrap mb-1">
          <span className={cn("text-xs font-semibold", meta.color)}>{event.from}</span>
          <span className="text-slate-300 dark:text-slate-600 text-[10px]">→</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">{event.to}</span>
          <span className={cn("text-[9px] font-semibold px-1.5 py-0.5 rounded border ml-auto", typeClass)}>
            {event.type}
          </span>
        </div>

        {/* Message */}
        <p className={cn(
          "text-xs leading-relaxed",
          isVeto ? "text-red-700 dark:text-red-300 font-medium" : "text-slate-700 dark:text-slate-200"
        )}>
          {message}
        </p>

        {/* Footer row */}
        <div className="flex items-center gap-3 mt-1.5">
          <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">{ts}</span>
          <span className="text-[10px] text-slate-300 dark:text-slate-600 font-mono uppercase">{event.domain}</span>
          {Object.keys(event.payload).length > 0 && (
            <span className="text-[10px] text-slate-300 dark:text-slate-600 font-mono truncate max-w-[260px]">
              {JSON.stringify(event.payload)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Page ────────────────────────────────────────────────────────── */
export default function A2AChatPage() {
  const { a2aFeed } = useErayaStore();
  const [domain, setDomain] = useState<Domain>("all");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [paused, setPaused] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [snapshotFeed, setSnapshotFeed] = useState<ChatEvent[]>([]);

  const liveEvents = a2aFeed as ChatEvent[];
  const source: ChatEvent[] = liveEvents.length > 0 ? liveEvents : DEMO_CHAT;

  /* Freeze display when paused */
  useEffect(() => {
    if (!paused) setSnapshotFeed(source);
  }, [source, paused]);

  const displayed = (paused ? snapshotFeed : source)
    .filter((e) => domain === "all" || e.domain === domain)
    .filter((e) => typeFilter === "all" || e.type === typeFilter);

  /* Auto-scroll */
  useEffect(() => {
    if (!paused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayed, paused]);

  const allTypes = Array.from(new Set(source.map((e) => e.type))).sort();
  const counts = { total: source.length, veto: source.filter((e) => e.type === "veto").length, live: liveEvents.length > 0 };

  return (
    <div className="max-w-5xl mx-auto h-full flex flex-col gap-4">

      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900/40 dark:to-cyan-900/20 shadow-sm">
            <Radio size={15} className="text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">A2A Chat Listener</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              Live inter-agent communication · {counts.total} messages
              {counts.veto > 0 && <span className="ml-2 text-red-500">· {counts.veto} veto{counts.veto > 1 ? "s" : ""}</span>}
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Live / demo badge */}
          <div className={cn(
            "flex items-center gap-1.5 text-[10px] px-2.5 py-1.5 rounded-lg border font-medium",
            counts.live
              ? "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800 text-emerald-600 dark:text-emerald-400"
              : "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400"
          )}>
            <div className={cn("w-1.5 h-1.5 rounded-full", counts.live ? "bg-emerald-500 animate-pulse" : "bg-amber-400")} />
            {counts.live ? "Live" : "Demo"}
          </div>

          {/* Pause / resume */}
          <button
            onClick={() => setPaused((v) => !v)}
            className={cn(
              "flex items-center gap-1.5 text-[11px] px-3 py-1.5 rounded-lg border transition-all font-medium",
              paused
                ? "bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800 text-orange-600 dark:text-orange-400"
                : "bg-white dark:bg-white/5 border-teal-100 dark:border-teal-900/30 text-slate-500 dark:text-slate-400 hover:text-teal-600"
            )}
          >
            {paused ? <><Play size={11} /> Resume</> : <><Pause size={11} /> Pause</>}
          </button>
        </div>
      </div>

      {/* ── Filters ─────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Domain tabs */}
        <div className="flex items-center gap-1 bg-white/70 dark:bg-white/5 border border-teal-100 dark:border-teal-900/30 rounded-xl p-1">
          {DOMAINS.map((d) => (
            <button
              key={d}
              onClick={() => setDomain(d)}
              className={cn(
                "text-[10px] font-semibold uppercase px-3 py-1 rounded-lg transition-all",
                domain === d
                  ? "bg-teal-500 text-white shadow-sm"
                  : "text-slate-400 dark:text-slate-500 hover:text-teal-600 dark:hover:text-teal-400"
              )}
            >
              {d === "all" ? "All" : d.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Type filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter size={11} className="text-slate-400" />
          {["all", ...allTypes].map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={cn(
                "text-[10px] px-2 py-0.5 rounded-lg border transition-all",
                typeFilter === t
                  ? (TYPE_STYLE[t] ?? "bg-teal-500 text-white border-teal-500")
                  : "text-slate-400 dark:text-slate-500 border-slate-200 dark:border-slate-700 hover:border-teal-200 dark:hover:border-teal-800"
              )}
            >
              {t === "all" ? "all types" : t}
            </button>
          ))}
        </div>
      </div>

      {/* ── Chat feed ───────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm"
        style={{ minHeight: 0, maxHeight: "calc(100vh - 260px)" }}
      >
        {displayed.length === 0 ? (
          <div className="flex items-center justify-center h-48 text-xs text-slate-400 dark:text-slate-600">
            No messages match the current filter.
          </div>
        ) : (
          <div className="p-3 space-y-1">
            {displayed.map((event) => (
              <Bubble key={event.id} event={event} />
            ))}
          </div>
        )}
      </div>

      {/* ── Role legend ─────────────────────────────────────────────── */}
      <div className="flex items-center gap-4 text-[10px] text-slate-400 dark:text-slate-500 pb-2">
        {Object.entries(ROLE_META).map(([role, m]) => (
          <div key={role} className="flex items-center gap-1.5">
            <div className={cn("w-3.5 h-3.5 rounded-full flex items-center justify-center text-white text-[7px] font-bold", m.bg)}>
              {m.abbr[0]}
            </div>
            <span className="capitalize">{role}</span>
          </div>
        ))}
        <span className="ml-auto">timestamps in local time · HH:MM:SS.mmm</span>
      </div>
    </div>
  );
}
