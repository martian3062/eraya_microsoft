import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatMs(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

export function formatTimestamp(ts: number | string): string {
  const d = typeof ts === "number" ? new Date(ts * 1000) : new Date(ts);
  return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export function tierColor(tier: string): string {
  return { HEAVY: "text-purple-600", MEDIUM: "text-blue-500", LIGHT: "text-slate-500" }[tier] ?? "text-slate-500";
}

export function statusColor(status: string): string {
  return {
    idle:        "text-slate-500",
    active:      "text-emerald-500",
    degraded:    "text-amber-500",
    quarantined: "text-red-500",
  }[status] ?? "text-slate-500";
}

export function severityColor(severity: string): string {
  return {
    low:      "text-slate-500",
    medium:   "text-amber-500",
    high:     "text-orange-500",
    critical: "text-red-500",
  }[severity] ?? "text-slate-500";
}
