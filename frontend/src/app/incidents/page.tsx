"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { Incident } from "@/lib/api";
import { AlertTriangle, CheckCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

export default function IncidentsPage() {
  const { data, mutate } = useSWR("incidents", () => api.incidents(), { refreshInterval: 10000 });
  const [resolving, setResolving] = useState<number | null>(null);
  const incidents = data?.results ?? [];
  const open = incidents.filter((i) => i.status !== "resolved").length;

  const handleResolve = async (id: number) => {
    setResolving(id);
    await api.resolveIncident(id);
    await mutate();
    setResolving(null);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-cyan-100 to-teal-100 dark:from-cyan-900/40 dark:to-teal-900/20 shadow-sm">
          <AlertTriangle size={16} className="text-cyan-600 dark:text-cyan-400" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">Incidents</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">{incidents.length} total · {open} open</p>
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm overflow-hidden">
        {incidents.length === 0 ? (
          <div className="peacock-card-fast p-12 text-center text-xs text-teal-600 dark:text-teal-400">
            No incidents recorded.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-teal-100 dark:border-teal-900/30 bg-gradient-to-r from-cyan-50 via-teal-50 to-emerald-50 dark:from-cyan-900/20 dark:via-teal-900/20 dark:to-emerald-900/10 text-xs text-slate-500 dark:text-slate-400">
                <th className="text-left px-4 py-3 font-medium">Severity</th>
                <th className="text-left px-4 py-3 font-medium">Title</th>
                <th className="text-left px-4 py-3 font-medium">Domain</th>
                <th className="text-left px-4 py-3 font-medium">Status</th>
                <th className="text-left px-4 py-3 font-medium">Detected</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody>
              {incidents.map((inc, idx) => (
                <IncidentRow
                  key={inc.id}
                  incident={inc}
                  idx={idx}
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

function IncidentRow({
  incident, idx, onResolve, resolving,
}: {
  incident: Incident; idx: number; onResolve: () => void; resolving: boolean;
}) {
  const isResolved = incident.status === "resolved";

  const severityBadge: Record<string, string> = {
    low:      "bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700",
    medium:   "bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800",
    high:     "bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-400 border border-orange-200 dark:border-orange-800",
    critical: "bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800",
  };
  const statusBadge: Record<string, string> = {
    open:          "text-red-500 dark:text-red-400",
    investigating: "text-amber-500 dark:text-amber-400",
    mitigating:    "text-cyan-600 dark:text-cyan-400",
    resolved:      "text-emerald-600 dark:text-emerald-400",
  };

  return (
    <tr
      className={cn(
        "border-b border-teal-50 dark:border-teal-900/20 transition-colors text-xs",
        idx % 2 === 0
          ? "bg-white/60 dark:bg-white/[0.03]"
          : "bg-teal-50/20 dark:bg-teal-900/10",
        "hover:bg-gradient-to-r hover:from-cyan-50/50 hover:to-teal-50/50 dark:hover:from-teal-900/20 dark:hover:to-cyan-900/10",
        isResolved && "opacity-50"
      )}
    >
      <td className="px-4 py-3">
        <span className={cn("text-[10px] px-2 py-0.5 rounded font-medium", severityBadge[incident.severity])}>
          {incident.severity}
        </span>
      </td>
      <td className="px-4 py-3 text-slate-700 dark:text-slate-200 max-w-xs truncate font-medium">{incident.title}</td>
      <td className="px-4 py-3 text-slate-400 dark:text-slate-500 font-mono">{incident.domain}</td>
      <td className={cn("px-4 py-3 font-semibold", statusBadge[incident.status])}>{incident.status}</td>
      <td className="px-4 py-3 text-slate-400 dark:text-slate-500">
        {new Date(incident.detected_at).toLocaleString()}
      </td>
      <td className="px-4 py-3 text-right">
        {!isResolved && (
          <button
            onClick={onResolve}
            disabled={resolving}
            className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 border border-emerald-200 dark:border-emerald-800 transition-colors disabled:opacity-40"
          >
            <CheckCircle size={10} />
            Resolve
          </button>
        )}
      </td>
    </tr>
  );
}
