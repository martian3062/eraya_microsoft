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
  return { HEAVY: "text-purple-400", MEDIUM: "text-blue-400", LIGHT: "text-slate-400" }[tier] ?? "text-slate-400";
}

export function statusColor(status: string): string {
  return {
    idle: "text-slate-400",
    active: "text-emerald-400",
    degraded: "text-yellow-400",
    quarantined: "text-red-400",
  }[status] ?? "text-slate-400";
}

export function severityColor(severity: string): string {
  return {
    low: "text-slate-400",
    medium: "text-yellow-400",
    high: "text-orange-400",
    critical: "text-red-400",
  }[severity] ?? "text-slate-400";
}
