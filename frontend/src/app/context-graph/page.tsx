"use client";
import { ContextGraph } from "@/components/graph/context-graph";
import { useState } from "react";

const DOMAINS = ["5g", "cloud", "icu"];

export default function ContextGraphPage() {
  const [domain, setDomain] = useState("5g");

  return (
    <div className="max-w-7xl mx-auto space-y-5 h-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-base font-semibold">ErayaGraph — Context Graph</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Shared memory graph. Nodes: entities (cells, patients, services). Edges: relationships.
          </p>
        </div>
        <div className="flex gap-2">
          {DOMAINS.map((d) => (
            <button
              key={d}
              onClick={() => setDomain(d)}
              className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                domain === d
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:bg-slate-700"
              }`}
            >
              {d === "5g" ? "5G" : d === "icu" ? "ICU" : "Cloud"}
            </button>
          ))}
        </div>
      </div>
      <div className="rounded-xl border border-[#1f2937] bg-[#111827]" style={{ height: "calc(100vh - 200px)" }}>
        <ContextGraph domain={domain} />
      </div>
    </div>
  );
}
