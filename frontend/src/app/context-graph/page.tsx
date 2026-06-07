"use client";
import { ContextGraph } from "@/components/graph/context-graph";
import { useState } from "react";
import { GitBranch } from "lucide-react";

const DOMAINS = ["5g", "cloud", "icu"];

export default function ContextGraphPage() {
  const [domain, setDomain] = useState("5g");

  return (
    <div className="max-w-7xl mx-auto space-y-4 h-full">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-gradient-to-br from-teal-100 to-cyan-100 dark:from-teal-900/40 dark:to-cyan-900/20 shadow-sm">
            <GitBranch size={16} className="text-teal-600 dark:text-teal-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-slate-800 dark:text-slate-100">ErayaGraph — Context Graph</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Shared memory graph. Nodes: entities. Edges: relationships &amp; causal paths.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {DOMAINS.map((d) => (
            <button
              key={d}
              onClick={() => setDomain(d)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                domain === d
                  ? "bg-gradient-to-r from-teal-500 to-cyan-500 text-white border-teal-400 shadow-sm"
                  : "bg-white/70 dark:bg-white/10 text-slate-500 dark:text-slate-400 border-teal-100 dark:border-teal-900/40 hover:border-teal-300 dark:hover:border-teal-700 hover:text-teal-600 dark:hover:text-teal-400"
              }`}
            >
              {d === "5g" ? "5G" : d === "icu" ? "ICU" : "Cloud"}
            </button>
          ))}
        </div>
      </div>
      <div
        className="rounded-2xl border border-teal-100 dark:border-teal-900/30 overflow-hidden shadow-sm"
        style={{
          height: "calc(100vh - 200px)",
          background: "var(--glass)",
          backdropFilter: "blur(12px)",
        }}
      >
        <ContextGraph domain={domain} />
      </div>
    </div>
  );
}
