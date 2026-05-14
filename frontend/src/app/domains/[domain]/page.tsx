"use client";
import { use } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { useWebSocket } from "@/hooks/use-websocket";
import { useState, useRef } from "react";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

const DOMAIN_META: Record<string, { title: string; subtitle: string; primaryMetric: string }> = {
  "5g": {
    title: "5G Self-Healing",
    subtitle: "Open5GS + UERANSIM · RAN telemetry stream",
    primaryMetric: "rsrp",
  },
  cloud: {
    title: "Cloud Cost Optimization",
    subtitle: "Kubernetes + OpenCost · workload metrics",
    primaryMetric: "cpu_util",
  },
  icu: {
    title: "ICU Patient Monitoring",
    subtitle: "MIMIC-IV synthetic stream · sepsis early warning",
    primaryMetric: "sepsis_risk",
  },
};

type SignalPoint = { t: string; [key: string]: number | string };

export default function DomainPage({ params }: { params: Promise<{ domain: string }> }) {
  const { domain } = use(params);
  const meta = DOMAIN_META[domain] ?? { title: domain, subtitle: "", primaryMetric: "value" };

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

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      {/* Header */}
      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-base font-semibold">{meta.title}</h1>
            <p className="text-xs text-slate-500 mt-0.5">{meta.subtitle}</p>
          </div>
          <StatusPills status={status} />
        </div>
      </div>

      {/* Chart */}
      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
        <div className="text-sm font-medium mb-4 capitalize">{primaryKey.replace(/_/g, " ")} over time</div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <XAxis dataKey="t" tick={{ fontSize: 10, fill: "#4b5563" }} />
            <YAxis tick={{ fontSize: 10, fill: "#4b5563" }} width={40} />
            <Tooltip
              contentStyle={{ background: "#111827", border: "1px solid #1f2937", fontSize: 11 }}
            />
            <Line
              type="monotone"
              dataKey={primaryKey}
              stroke="#6366f1"
              dot={false}
              strokeWidth={1.5}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Live signal table */}
      <div className="rounded-xl border border-[#1f2937] bg-[#111827] p-5">
        <div className="text-sm font-medium mb-3">Live Signal Sources</div>
        <div className="space-y-3">
          {Object.entries(latestSignals).length === 0 ? (
            <p className="text-slate-600 text-xs py-4 text-center">
              No live signals — connect WebSocket or start the domain simulator.
            </p>
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
        <div key={k} className="bg-slate-800 rounded-lg px-3 py-1.5 text-center">
          <div className="text-[10px] text-slate-500">{k.replace(/_/g, " ")}</div>
          <div className="text-xs font-mono font-medium text-slate-200">{String(v)}</div>
        </div>
      ))}
    </div>
  );
}

function SignalRow({ source, features, highlight }: { source: string; features: Record<string, number>; highlight: string }) {
  return (
    <div className="rounded-lg border border-[#1f2937] p-3">
      <div className="text-xs font-mono text-slate-400 mb-2">{source}</div>
      <div className="flex flex-wrap gap-3">
        {Object.entries(features).slice(0, 8).map(([k, v]) => (
          <div key={k} className={k === highlight ? "text-indigo-400" : "text-slate-400"}>
            <span className="text-[10px]">{k}: </span>
            <span className="text-[11px] font-mono font-medium">{typeof v === "number" ? v.toFixed(2) : v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
