"use client";
import { Bell, RefreshCw, LogOut, UserCheck, User, Home, ChevronRight, Moon, Sun } from "lucide-react";
import { useErayaStore } from "@/store";
import { useAuthStore } from "@/store/auth";
import { useThemeStore } from "@/store/theme";
import { useWebSocket } from "@/hooks/use-websocket";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { signOut, useSession } from "next-auth/react";
import Link from "next/link";
import Image from "next/image";
import { cn } from "@/lib/utils";

const SEGMENT_LABELS: Record<string, string> = {
  dashboard:       "Dashboard",
  agents:          "Agents",
  perceiver:       "Perceiver",
  planner:         "Planner",
  recoverer:       "Recoverer",
  guardian:        "Guardian",
  domains:         "Domains",
  "5g":            "5G",
  cloud:           "Cloud",
  icu:             "ICU",
  security:        "Security",
  "attack-console":"Attack Console",
  pentest:         "Network Scan",
  network:         "Network",
  incidents:       "Incidents",
  "audit-log":     "Audit Log",
  "context-graph": "Context Graph",
  "a2a-chat":      "A2A Chat",
  "self-healing":  "Self-Healing Monitor",
  map:             "Global Operations Map",
  settings:        "Settings",
};

function useBreadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  return segments.map((seg, i) => ({
    label: SEGMENT_LABELS[seg] ?? seg,
    href: "/" + segments.slice(0, i + 1).join("/"),
    isLast: i === segments.length - 1,
  }));
}

export function Header() {
  const { guardianAlerts, resetGuardianAlerts, setWsConnected, pushA2AEvent, updateAgent } = useErayaStore();
  const { user, logout } = useAuthStore();
  const { dark, toggle } = useThemeStore();
  const { data: session } = useSession();
  const router = useRouter();
  const breadcrumbs = useBreadcrumbs();
  const isHome = breadcrumbs.length === 1 && breadcrumbs[0]?.href === "/dashboard";

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

  useEffect(() => { setWsConnected(connected); }, [connected, setWsConnected]);

  async function handleLogout() {
    logout();
    if (session) {
      await signOut({ callbackUrl: "/" });
    } else {
      router.replace("/");
    }
  }

  const isGuest = user?.role === "guest";

  return (
    <header
      className="h-12 flex items-center justify-between px-4 flex-shrink-0 relative z-10"
      style={{
        background: "var(--glass)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        borderBottom: "1px solid var(--glass-border)",
        boxShadow: "0 2px 12px var(--glass-shadow)",
      }}
    >
      {/* ── Left ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        <Link
          href="/dashboard"
          className={cn(
            "flex items-center justify-center w-7 h-7 rounded-lg transition-all",
            isHome
              ? "bg-teal-100 dark:bg-teal-900/40 text-teal-600 shadow-sm border border-teal-200 dark:border-teal-700"
              : "text-slate-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 hover:text-teal-600"
          )}
          title="Dashboard"
        >
          <Home size={13} />
        </Link>

        {!isHome && breadcrumbs.length > 0 && (
          <nav className="flex items-center gap-1">
            {breadcrumbs.map((crumb, i) => (
              <span key={crumb.href} className="flex items-center gap-1">
                {i > 0 && <ChevronRight size={11} className="text-slate-300 dark:text-slate-600" />}
                {crumb.isLast ? (
                  <span className="text-xs font-semibold text-teal-700 dark:text-teal-400">{crumb.label}</span>
                ) : (
                  <Link
                    href={crumb.href}
                    className="text-xs text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
                  >
                    {crumb.label}
                  </Link>
                )}
              </span>
            ))}
          </nav>
        )}
      </div>

      {/* ── Right ───────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Live indicator */}
        <div className={cn(
          "flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-lg",
          connected
            ? "bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400 border border-emerald-100 dark:border-emerald-800"
            : "bg-slate-100 dark:bg-slate-800 text-slate-400"
        )}>
          <RefreshCw size={9} className={connected ? "animate-spin" : ""} />
          {connected ? "Live" : "…"}
        </div>

        {/* Notifications */}
        <button
          onClick={resetGuardianAlerts}
          className="relative p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors"
        >
          <Bell size={14} />
          {guardianAlerts > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] flex items-center justify-center text-white">
              {guardianAlerts > 9 ? "9+" : guardianAlerts}
            </span>
          )}
        </button>

        {/* Theme toggle */}
        <button
          onClick={toggle}
          className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 dark:hover:bg-teal-900/20 transition-colors"
          title={dark ? "Light mode" : "Dark mode"}
        >
          {dark ? <Sun size={14} /> : <Moon size={14} />}
        </button>

        {/* User chip */}
        {user && (
          <div className={cn(
            "flex items-center gap-1.5 text-[10px] px-2 py-1 rounded-full border font-medium",
            isGuest
              ? "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800 text-blue-600 dark:text-blue-400"
              : "bg-teal-50 dark:bg-teal-900/20 border-teal-200 dark:border-teal-800 text-teal-700 dark:text-teal-400"
          )}>
            {user.image ? (
              <Image src={user.image} alt={user.name} width={18} height={18} className="rounded-full" />
            ) : isGuest ? (
              <User size={10} />
            ) : (
              <UserCheck size={10} />
            )}
            <span>{user.name.split(" ")[0]}</span>
          </div>
        )}

        {/* Logout */}
        <button
          onClick={handleLogout}
          className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
          title="Sign out"
        >
          <LogOut size={13} />
        </button>
      </div>
    </header>
  );
}
