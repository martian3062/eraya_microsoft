"use client";
import { useErayaStore } from "@/store";
import { formatTimestamp } from "@/lib/utils";
import { cn } from "@/lib/utils";

const TYPE_COLORS: Record<string, string> = {
  "context.update": "text-blue-400",
  "action.request": "text-indigo-400",
  "action.response": "text-emerald-400",
  veto: "text-red-400",
  heartbeat: "text-slate-500",
  "capability.query": "text-purple-400",
  quarantine: "text-red-500",
};

export function A2AFeed({ maxItems = 50 }: { maxItems?: number }) {
  const { a2aFeed } = useErayaStore();
  const items = a2aFeed.slice(0, maxItems);

  if (items.length === 0) {
    return (
      <div className="text-slate-600 text-xs text-center py-8">
        Waiting for A2A messages…
      </div>
    );
  }

  return (
    <div className="space-y-0.5 overflow-y-auto max-h-80 font-mono text-[11px]">
      {items.map((event) => (
        <div
          key={event.id}
          className={cn(
            "flex items-baseline gap-2 px-2 py-1 rounded hover:bg-white/5 transition-colors",
            event.type === "veto" && "bg-red-950/30"
          )}
        >
          <span className="text-slate-600 w-16 flex-shrink-0">
            {formatTimestamp(event.timestamp)}
          </span>
          <span className={cn("w-28 flex-shrink-0 truncate", TYPE_COLORS[event.type] ?? "text-slate-400")}>
            {event.type}
          </span>
          <span className="text-slate-400 truncate">
            <span className="text-slate-300">{event.from}</span>
            <span className="text-slate-600"> → </span>
            <span className="text-slate-300">{event.to}</span>
            <span className="text-slate-600 ml-2">[{event.domain}]</span>
          </span>
        </div>
      ))}
    </div>
  );
}
