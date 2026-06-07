"use client";
import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/use-websocket";
import { useState, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";
import { Activity } from "lucide-react";
import { useThemeStore } from "@/store/theme";

const DOMAIN_META: Record<string, { title: string; subtitle: string; primaryMetric: string; color: string }> = {
  "5g": {
    title: "5G Self-Healing",
    subtitle: "Open5GS + UERANSIM · RAN telemetry stream",
    primaryMetric: "rsrp",
    color: "from-teal-400 to-cyan-400",
  },
  cloud: {
    title: "Cloud Cost Optimization",
    subtitle: "Kubernetes + OpenCost · workload metrics",
    primaryMetric: "cpu_util",
    color: "from-cyan-400 to-sky-400",
  },
  icu: {
    title: "ICU Patient Monitoring",
    subtitle: "MIMIC-IV synthetic stream · sepsis early warning",
    primaryMetric: "sepsis_risk",
    color: "from-emerald-400 to-teal-400",
  },
  network: {
    title: "Network Intelligence",
    subtitle: "Wi-Fi signal monitoring · device telemetry · anomaly detection",
    primaryMetric: "rssi",
    color: "from-violet-400 to-indigo-400",
  },
};

type SignalPoint = { t: string; [key: string]: number | string };

export default function DomainPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = use(params);
  const meta = DOMAIN_META[domain] ?? { title: domain, subtitle: "", primaryMetric: "value", color: "from-teal-400 to-cyan-400" };
  const dark = useThemeStore((s) => s.dark);

  const { data: status } = useSWR(`domain-status-${domain}`, () => api.domainStatus(domain), {
    refreshInterval: 5000,
  });
  const { data: initialSignals } = useSWR(`domain-signals-${domain}`, () => api.domainSignals(domain));

  const [chart, setChart] = useState<SignalPoint[]>([]);
  const [latestSignals, setLatestSignals] = useState<Record<string, Record<string, number>>>({});
  const chartRef = useRef(chart);
  chartRef.current = chart;

  useWebSocket(domain, {
    onMessage: (msg) => {
      if (msg.type === "domain.signal" && msg.data) {
        const { source, features, timestamp } = msg.data as {
          source: string;
          features: Record<string, number>;
          timestamp: number;
        };
        const point: SignalPoint = {
          t: new Date(timestamp * 1000).toLocaleTimeString("en-US", { hour12: false }),
          ...features,
        };
        setChart((prev) => [...prev.slice(-59), point]);
        setLatestSignals((prev) => ({ ...prev, [source]: features }));
      }
    },
  });

  const primaryKey = meta.primaryMetric;
  const chartData = chart.length > 0
    ? chart
    : (initialSignals?.signals ?? []).map((s) => ({
        t: new Date(s.timestamp * 1000).toLocaleTimeString("en-US", { hour12: false }),
        ...s.features,
      }));

  const tooltipStyle = dark
    ? { background: "rgba(8,16,30,0.92)", border: "1px solid #0d4a40", borderRadius: 8, fontSize: 11, color: "#e2e8f0" }
    : { background: "rgba(255,255,255,0.95)", border: "1px solid #99f6e4", borderRadius: 8, fontSize: 11, color: "#1e293b" };

  return (
    <div className="max-w-6xl mx-auto space-y-5">

      {/* Header */}
      <div className="peacock-card flex items-center justify-between p-5 rounded-2xl border border-teal-200 dark:border-teal-800/50 shadow-sm">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl bg-gradient-to-br ${meta.color} shadow-sm opacity-90`}>
            <Activity size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">{meta.title}</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{meta.subtitle}</p>
          </div>
        </div>
        <StatusPills status={status} />
      </div>

      {/* Chart */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-2.5 h-2.5 rounded-full bg-gradient-to-r ${meta.color}`} />
          <div className="text-sm font-semibold text-slate-700 dark:text-slate-200 capitalize">
            {primaryKey.replace(/_/g, " ")} — live stream
          </div>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: dark ? "#64748b" : "#94a3b8" }} />
            <YAxis tick={{ fontSize: 10, fill: dark ? "#64748b" : "#94a3b8" }} width={40} />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey={primaryKey}
              stroke="#14b8a6"
              dot={false}
              strokeWidth={2}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Live signals */}
      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5">
        <div className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-3">Live Signal Sources</div>
        <div className="space-y-3">
          {Object.entries(latestSignals).length === 0 ? (
            <div className="peacock-card-fast rounded-xl p-6 text-center text-xs text-teal-600 dark:text-teal-400">
              No live signals — connect WebSocket or start the domain simulator.
            </div>
          ) : (
            Object.entries(latestSignals).map(([source, features]) => (
              <SignalRow key={source} source={source} features={features} highlight={primaryKey} />
            ))
          )}
        </div>
      </div>
    </div>
  );
}

function StatusPills({ status }: { status: Record<string, unknown> | undefined }) {
  if (!status) return null;
  const entries = Object.entries(status).filter(([k]) => !["domain", "status"].includes(k));
  return (
    <div className="flex gap-2 flex-wrap">
      {entries.slice(0, 4).map(([k, v]) => (
        <div key={k} className="bg-white/80 dark:bg-white/10 border border-teal-100 dark:border-teal-900/40 rounded-xl px-3 py-1.5 text-center shadow-sm">
          <div className="text-[10px] text-slate-400 dark:text-slate-500">{k.replace(/_/g, " ")}</div>
          <div className="text-xs font-mono font-semibold text-teal-700 dark:text-teal-400">{String(v)}</div>
        </div>
      ))}
    </div>
  );
}

function SignalRow({ source, features, highlight }: {
  source: string; features: Record<string, number>; highlight: string;
}) {
  return (
    <div className="rounded-xl border border-teal-100 dark:border-teal-900/30 bg-gradient-to-r from-teal-50/50 via-white to-cyan-50/50 dark:from-teal-900/20 dark:via-transparent dark:to-cyan-900/10 p-3">
      <div className="text-xs font-mono text-teal-600 dark:text-teal-400 mb-2">{source}</div>
      <div className="flex flex-wrap gap-3">
        {Object.entries(features).slice(0, 8).map(([k, v]) => (
          <div key={k} className={k === highlight ? "text-teal-600 dark:text-teal-400" : "text-slate-500 dark:text-slate-400"}>
            <span className="text-[10px]">{k}: </span>
            <span className={`text-[11px] font-mono font-semibold ${k === highlight ? "text-teal-700 dark:text-teal-300" : ""}`}>
              {typeof v === "number" ? v.toFixed(2) : v}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
