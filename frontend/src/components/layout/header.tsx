"use client";
import { Shield, Bell, RefreshCw } from "lucide-react";
import { useErayaStore } from "@/store";
import { useWebSocket } from "@/hooks/use-websocket";
import { useEffect } from "react";
import { cn } from "@/lib/utils";

export function Header() {
  const { guardianAlerts, resetGuardianAlerts, setWsConnected, pushA2AEvent, updateAgent } = useErayaStore();

  const { connected } = useWebSocket("swarm", {
    onMessage: (msg) => {
      if (msg.type === "a2a.message" && msg.data) {
        pushA2AEvent({
          id: String(msg.data.message_id ?? Date.now()),
          from: String(msg.data.from_agent ?? ""),
          to: String(msg.data.to_agent ?? ""),
          type: String(msg.data.message_type ?? ""),
          domain: String(msg.data.domain ?? ""),
          timestamp: String(msg.data.timestamp ?? new Date().toISOString()),
          payload: (msg.data.payload as Record<string, unknown>) ?? {},
        });
      }
      if (msg.type === "agent.status" && msg.data) {
        updateAgent(String(msg.data.agent_id), msg.data as Record<string, unknown>);
      }
    },
  });

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  return (
    <header className="h-12 flex items-center justify-between px-6 border-b border-[#1f2937] bg-[#111827] flex-shrink-0">
      <div className="flex items-center gap-3">
        <Shield size={16} className="text-indigo-400" />
        <span className="text-sm text-slate-300 font-medium">Operator Console</span>
        <span className="text-[10px] bg-indigo-900/40 text-indigo-400 border border-indigo-800 rounded px-1.5 py-0.5">
          Microsoft Build 2026
        </span>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={resetGuardianAlerts}
          className="relative p-1.5 rounded-md text-slate-400 hover:text-slate-200 hover:bg-white/5 transition-colors"
        >
          <Bell size={15} />
          {guardianAlerts > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-600 rounded-full text-[9px] flex items-center justify-center text-white">
              {guardianAlerts > 9 ? "9+" : guardianAlerts}
            </span>
          )}
        </button>

        <div className={cn(
          "flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-md",
          connected ? "bg-emerald-950/50 text-emerald-400" : "bg-slate-800 text-slate-500"
        )}>
          <RefreshCw size={10} className={connected ? "animate-spin" : ""} />
          {connected ? "Live stream" : "Reconnecting"}
        </div>
      </div>
    </header>
  );
}
