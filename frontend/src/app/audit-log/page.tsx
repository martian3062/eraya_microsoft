"use client";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { AuditEntry } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function AuditLogPage() {
  const { data } = useSWR("audit-log", () => api.auditLog(), { refreshInterval: 15000 });
  const entries = data?.results ?? [];

  const verdictColor: Record<string, string> = {
    approve: "text-emerald-400 bg-emerald-900/30",
    warn: "text-yellow-400 bg-yellow-900/30",
    block: "text-orange-400 bg-orange-900/30",
    quarantine: "text-red-400 bg-red-900/30",
  };

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-base font-semibold">Guardian Audit Log</h1>
        <p className="text-xs text-slate-500 mt-0.5">
          Every critical decision is HMAC-SHA256 signed. {entries.length} records loaded.
        </p>
      </div>

      <div className="rounded-xl border border-[#1f2937] bg-[#111827] overflow-hidden">
        {entries.length === 0 ? (
          <div className="text-slate-600 text-xs py-12 text-center">No audit records. Guardian hasn't evaluated any actions yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-[#1f2937] text-slate-500">
                  <th className="text-left px-4 py-3">Timestamp</th>
                  <th className="text-left px-4 py-3">Agent</th>
                  <th className="text-left px-4 py-3">Domain</th>
                  <th className="text-left px-4 py-3">Verdict</th>
                  <th className="text-left px-4 py-3">Violations</th>
                  <th className="text-left px-4 py-3 font-mono">Hash</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((entry) => (
                  <tr key={entry.id} className="border-b border-[#1f2937] hover:bg-white/3">
                    <td className="px-4 py-2.5 text-slate-500 font-mono">
                      {new Date(entry.timestamp).toLocaleString()}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-300">{entry.agent_id}</td>
                    <td className="px-4 py-2.5 text-slate-400">{entry.domain}</td>
                    <td className="px-4 py-2.5">
                      <span className={cn("px-2 py-0.5 rounded text-[10px] font-medium", verdictColor[entry.verdict] ?? verdictColor.approve)}>
                        {entry.verdict}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-500">
                      {Array.isArray(entry.violations) ? entry.violations.length : 0}
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-600 text-[10px]">
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
