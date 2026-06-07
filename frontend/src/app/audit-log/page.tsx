"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { AuditEntry } from "@/lib/api";
import { cn } from "@/lib/utils";
import { ShieldCheck } from "lucide-react";

export default function AuditLogPage() {
  const { data } = useSWR("audit-log", () => api.auditLog(), { refreshInterval: 15000 });
  const entries = data?.results ?? [];

  const verdictColor: Record<string, string> = {
    approve:    "text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800",
    warn:       "text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800",
    block:      "text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800",
    quarantine: "text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800",
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div className="flex items-center gap-3">
        <div className="p-2 rounded-xl bg-gradient-to-br from-teal-100 to-emerald-100 dark:from-teal-900/40 dark:to-emerald-900/20 shadow-sm">
          <ShieldCheck size={16} className="text-teal-600 dark:text-teal-400" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">Guardian Audit Log</h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Every critical decision is HMAC-SHA256 signed. {entries.length} records loaded.
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm overflow-hidden">
        {entries.length === 0 ? (
          <div className="peacock-card-fast p-12 text-center text-xs text-teal-600 dark:text-teal-400">
            No audit records yet — Guardian hasn&apos;t evaluated any actions.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-teal-100 dark:border-teal-900/30 bg-gradient-to-r from-teal-50 via-cyan-50 to-emerald-50 dark:from-teal-900/20 dark:via-cyan-900/10 dark:to-emerald-900/10 text-slate-500 dark:text-slate-400">
                  <th className="text-left px-4 py-3 font-medium">Timestamp</th>
                  <th className="text-left px-4 py-3 font-medium">Agent</th>
                  <th className="text-left px-4 py-3 font-medium">Domain</th>
                  <th className="text-left px-4 py-3 font-medium">Verdict</th>
                  <th className="text-left px-4 py-3 font-medium">Violations</th>
                  <th className="text-left px-4 py-3 font-medium font-mono">Hash</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry, idx) => (
                  <tr
                    key={entry.id}
                    className={cn(
                      "border-b border-teal-50 dark:border-teal-900/20 transition-colors",
                      idx % 2 === 0
                        ? "bg-white/60 dark:bg-white/[0.03]"
                        : "bg-teal-50/30 dark:bg-teal-900/10",
                      "hover:bg-gradient-to-r hover:from-teal-50/60 hover:to-cyan-50/60 dark:hover:from-teal-900/20 dark:hover:to-cyan-900/10"
                    )}
                  >
                    <td className="px-4 py-2.5 text-slate-400 dark:text-slate-500 font-mono">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-700 dark:text-slate-200">{entry.agent_id}</td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{entry.domain}</td>
                    <td className="px-4 py-2.5">
                      <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium", verdictColor[entry.verdict] ?? verdictColor.approve)}>
                        {entry.verdict}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">
                      {Array.isArray(entry.violations) ? entry.violations.length : 0}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-teal-500 dark:text-teal-400 text-[10px]">
                      {String(entry.record_id ?? "").slice(0, 12)}…
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
