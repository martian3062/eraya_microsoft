"use client";
import { useErayaStore } from "@/store";
import { formatTimestamp } from "@/lib/utils";
import { cn } from "@/lib/utils";

const now = () => new Date().toISOString();
const DEMO_EVENTS = [
  { id:"d1",  from:"perceiver-5g-001",   to:"planner-5g-001",     type:"context.update",   domain:"5g",      timestamp: now(), payload:{rsrp:-87.4} },
  { id:"d2",  from:"planner-5g-001",     to:"recoverer-5g-001",   type:"action.request",   domain:"5g",      timestamp: now(), payload:{action:"handover"} },
  { id:"d3",  from:"guardian-5g-001",    to:"planner-5g-001",     type:"veto",             domain:"5g",      timestamp: now(), payload:{rule:"R002"} },
  { id:"d4",  from:"perceiver-cloud-001",to:"planner-cloud-001",  type:"context.update",   domain:"cloud",   timestamp: now(), payload:{cpu:84.2} },
  { id:"d5",  from:"planner-cloud-001",  to:"recoverer-cloud-001",type:"action.request",   domain:"cloud",   timestamp: now(), payload:{action:"scale_down"} },
  { id:"d6",  from:"recoverer-cloud-001",to:"planner-cloud-001",  type:"action.response",  domain:"cloud",   timestamp: now(), payload:{ok:true} },
  { id:"d7",  from:"perceiver-icu-001",  to:"planner-icu-001",    type:"context.update",   domain:"icu",     timestamp: now(), payload:{hrv:42} },
  { id:"d8",  from:"guardian-icu-001",   to:"planner-icu-001",    type:"capability.query", domain:"icu",     timestamp: now(), payload:{} },
  { id:"d9",  from:"planner-icu-001",    to:"recoverer-icu-001",  type:"action.request",   domain:"icu",     timestamp: now(), payload:{action:"alert_nurse"} },
  { id:"d10", from:"perceiver-net-001",  to:"planner-net-001",    type:"context.update",   domain:"network", timestamp: now(), payload:{rssi:-71} },
  { id:"d11", from:"guardian-net-001",   to:"planner-net-001",    type:"veto",             domain:"network", timestamp: now(), payload:{rule:"R003"} },
  { id:"d12", from:"planner-net-001",    to:"recoverer-net-001",  type:"action.request",   domain:"network", timestamp: now(), payload:{action:"reroute"} },
];

const TYPE_COLORS: Record<string, string> = {
  "context.update":   "text-blue-500 dark:text-blue-400",
  "action.request":   "text-orange-500 dark:text-orange-400",
  "action.response":  "text-emerald-500 dark:text-emerald-400",
  veto:               "text-red-500 dark:text-red-400",
  heartbeat:          "text-slate-400 dark:text-slate-500",
  "capability.query": "text-purple-500 dark:text-purple-400",
  quarantine:         "text-red-600 dark:text-red-400",
};

export function A2AFeed({ maxItems = 50 }: { maxItems?: number }) {
  const { a2aFeed } = useErayaStore();
  const live = a2aFeed.slice(0, maxItems);
  const items = live.length > 0 ? live : DEMO_EVENTS;

  return (
    <div className="space-y-0.5 overflow-y-auto max-h-80 font-mono text-[11px]">
      {items.map((event) => (
        <div
          key={event.id}
          className={cn(
            "flex items-baseline gap-2 px-2 py-1 rounded transition-colors",
            event.type === "veto"
              ? "bg-red-50 dark:bg-red-900/20"
              : "hover:bg-orange-50/60 dark:hover:bg-teal-900/20"
          )}
        >
          <span className="text-slate-400 dark:text-slate-600 w-16 flex-shrink-0">
            {formatTimestamp(event.timestamp)}
          </span>
          <span className={cn("w-28 flex-shrink-0 truncate", TYPE_COLORS[event.type] ?? "text-slate-500")}>
            {event.type}
          </span>
          <span className="text-slate-500 dark:text-slate-400 truncate">
            <span className="text-slate-700 dark:text-slate-200">{event.from}</span>
            <span className="text-slate-300 dark:text-slate-600"> → </span>
            <span className="text-slate-700 dark:text-slate-200">{event.to}</span>
            <span className="text-slate-400 dark:text-slate-500 ml-2">[{event.domain}]</span>
          </span>
        </div>
      ))}
    </div>
  );
}
