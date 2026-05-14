"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/api";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { cn, severityColor } from "@/lib/utils";
import { useState } from "react";

export default function IncidentsPage() {
  const { data, mutate } = useSWR("incidents", () => api.incidents(), { refreshInterval: 10000 });
  const [resolving, setResolving] = useState<number | null>(null);

  const incidents = data?.results ?? [];

  const handleResolve = async (id: number) => {
    setResolving(id);
    await api.resolveIncident(id);
    await mutate();
    setResolving(null);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold">Incidents</h1>
          <p className="text-xs text-slate-500 mt-0.5">{incidents.length} total · {incidents.filter(i => i.status !== "resolved").length} open</p>
        </div>
      </div>

      <div className="rounded-xl border border-[#1f2937] bg-[#111827] overflow-hidden">
        {incidents.length === 0 ? (
          <div className="text-slate-600 text-xs py-12 text-center">No incidents recorded.</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#1f2937] text-xs text-slate-500">
                <th className="text-left px-4 py-3">Severity</th>
                <th className="text-left px-4 py-3">Title</th>
                <th className="text-left px-4 py-3">Domain</th>
                <th className="text-left px-4 py-3">Status</th>
                <th className="text-left px-4 py-3">Detected</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc) => (
                <IncidentRow
                  key={inc.id}
                  incident={inc}
                  onResolve={() => handleResolve(inc.id)}
                  resolving={resolving === inc.id}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function IncidentRow({ incident, onResolve, resolving }: { incident: Incident; onResolve: () => void; resolving: boolean }) {
  const isResolved = incident.status === "resolved";
  const severityBadge: Record<string, string> = {
    low: "bg-slate-800 text-slate-400",
    medium: "bg-yellow-900/50 text-yellow-400",
    high: "bg-orange-900/50 text-orange-400",
    critical: "bg-red-900/60 text-red-400",
  };
  const statusBadge: Record<string, string> = {
    open: "text-red-400",
    investigating: "text-yellow-400",
    mitigating: "text-blue-400",
    resolved: "text-emerald-400",
  };
  return (
    <tr className={cn("border-b border-[#1f2937] hover:bg-white/3 transition-colors", isResolved && "opacity-50")}>
      <td className="px-4 py-3">
        <span className={cn("text-[10px] px-2 py-0.5 rounded font-medium", severityBadge[incident.severity])}>
          {incident.severity}
        </span>
      </td>
      <td className="px-4 py-3 text-sm text-slate-200 max-w-xs truncate">{incident.title}</td>
      <td className="px-4 py-3 text-xs text-slate-400 font-mono">{incident.domain}</td>
      <td className={cn("px-4 py-3 text-xs font-medium", statusBadge[incident.status])}>{incident.status}</td>
      <td className="px-4 py-3 text-xs text-slate-500">
        {new Date(incident.detected_at).toLocaleString()}
      </td>
      <td className="px-4 py-3 text-right">
        {!isResolved && (
          <button
            onClick={onResolve}
            disabled={resolving}
            className="flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-emerald-900/40 text-emerald-400 hover:bg-emerald-900 transition-colors disabled:opacity-40"
          >
            <CheckCircle size={10} />
            Resolve
          </button>
        )}
      </td>
    </tr>
  );
}
