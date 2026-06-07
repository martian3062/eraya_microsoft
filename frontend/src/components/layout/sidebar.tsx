"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Bot, Activity, GitBranch,
  AlertTriangle, FileText, Settings, Shield, Radio, HeartPulse, Map,
} from "lucide-react";
import { useErayaStore } from "@/store";
import { useAuthStore } from "@/store/auth";

const MAJOR = [
  {
    id: "dashboard",
    icon: LayoutDashboard,
    label: "Home",
    href: "/dashboard",
    match: ["/dashboard"],
  },
  {
    id: "agents",
    icon: Bot,
    label: "Agents",
    href: "/agents/perceiver",
    match: ["/agents"],
    children: [
      { label: "Perceiver",  href: "/agents/perceiver" },
      { label: "Planner",    href: "/agents/planner" },
      { label: "Recoverer",  href: "/agents/recoverer" },
      { label: "Guardian",   href: "/agents/guardian" },
    ],
  },
  {
    id: "domains",
    icon: Activity,
    label: "Domains",
    href: "/domains/5g",
    match: ["/domains"],
    children: [
      { label: "5G Self-Healing", href: "/domains/5g" },
      { label: "Cloud Cost",      href: "/domains/cloud" },
      { label: "ICU Monitoring",  href: "/domains/icu" },
      { label: "Network",         href: "/domains/network" },
    ],
  },
  {
    id: "security",
    icon: Shield,
    label: "Security",
    href: "/security/attack-console",
    match: ["/security"],
    children: [
      { label: "Attack Console", href: "/security/attack-console" },
      { label: "Network Scan",   href: "/security/pentest" },
    ],
  },
];

const FLAT = [
  { label: "Global Map",    href: "/map",           icon: Map },
  { label: "A2A Chat",      href: "/a2a-chat",      icon: Radio },
  { label: "Self-Heal",     href: "/self-healing",  icon: HeartPulse },
  { label: "Context Graph", href: "/context-graph", icon: GitBranch },
  { label: "Incidents",     href: "/incidents",     icon: AlertTriangle },
  { label: "Audit Log",     href: "/audit-log",     icon: FileText },
  { label: "Settings",      href: "/settings",      icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { guardianAlerts, wsConnected } = useErayaStore();
  const user = useAuthStore((s) => s.user);
  const isGuest = user?.role === "guest";

  const activeSection = MAJOR.find(
    (s) => s.match?.some((m) => pathname.startsWith(m)) ?? pathname === s.href
  );

  return (
    <aside
      className="w-56 flex-shrink-0 flex flex-col relative z-20"
      style={{
        background: "var(--glass)",
        backdropFilter: "blur(18px)",
        WebkitBackdropFilter: "blur(18px)",
        borderRight: "1px solid var(--glass-border)",
        boxShadow: "2px 0 20px var(--glass-shadow)",
      }}
    >
      {/* ── Logo ───────────────────────────────────────────────────── */}
      <div className="px-4 py-4 border-b border-teal-100/60 dark:border-teal-900/30">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-orange-400 to-teal-400 flex items-center justify-center text-white font-bold text-xs shadow-sm">
            E
          </div>
          <div>
            <div className="text-sm font-bold tracking-wide text-slate-800 dark:text-slate-100">ERAYA</div>
            <div className="text-[10px] text-slate-400 dark:text-slate-500 -mt-0.5">Agent Swarm</div>
          </div>
        </div>
      </div>

      {/* ── Major icon strip ───────────────────────────────────────── */}
      <div className="px-3 py-3 border-b border-teal-100/60 dark:border-teal-900/30">
        <div className="grid grid-cols-4 gap-1">
          {MAJOR.map((sec) => {
            const Icon = sec.icon;
            const isActive = activeSection?.id === sec.id;
            const hasAlert = sec.id === "security" && guardianAlerts > 0;
            return (
              <Link
                key={sec.id}
                href={sec.href}
                title={sec.label}
                className={cn(
                  "relative flex flex-col items-center gap-1 py-2 rounded-xl text-[9px] font-medium transition-all",
                  isActive
                    ? "bg-gradient-to-b from-teal-100 to-cyan-100 dark:from-teal-900/40 dark:to-cyan-900/30 text-teal-700 dark:text-teal-300 shadow-sm border border-teal-200 dark:border-teal-800"
                    : "text-slate-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 hover:text-teal-600 dark:hover:text-teal-400"
                )}
              >
                <Icon size={15} />
                <span>{sec.label}</span>
                {hasAlert && (
                  <span className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-red-500 rounded-full text-[8px] text-white flex items-center justify-center">
                    {guardianAlerts > 9 ? "9" : guardianAlerts}
                  </span>
                )}
              </Link>
            );
          })}
        </div>
      </div>

      {/* ── Accordion subitems ─────────────────────────────────────── */}
      {activeSection?.children && activeSection.children.length > 0 && (
        <div className="px-3 py-2 border-b border-teal-100/60 dark:border-teal-900/30">
          <div className="text-[9px] font-semibold text-teal-500 dark:text-teal-600 uppercase tracking-widest mb-1.5 px-1">
            {activeSection.label}
          </div>
          <div className="space-y-0.5">
            {activeSection.children.map((child) => {
              const isActive = pathname === child.href;
              return (
                <Link
                  key={child.href}
                  href={child.href}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs transition-all",
                    isActive
                      ? "bg-gradient-to-r from-teal-100 to-cyan-50 dark:from-teal-900/40 dark:to-cyan-900/20 text-teal-700 dark:text-teal-300 font-semibold border border-teal-200/60 dark:border-teal-800/50"
                      : "text-slate-500 dark:text-slate-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 hover:text-teal-600 dark:hover:text-teal-400"
                  )}
                >
                  <span
                    className={cn(
                      "w-1.5 h-1.5 rounded-full flex-shrink-0",
                      isActive ? "bg-teal-500" : "bg-slate-300 dark:bg-slate-600"
                    )}
                  />
                  {child.label}
                </Link>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Flat nav items ─────────────────────────────────────────── */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-0.5">
        {FLAT.map(({ label, href, icon: Icon }) => {
          const isActive = pathname === href;
          const badge = label === "Incidents" && guardianAlerts > 0 ? guardianAlerts : undefined;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2 rounded-lg px-3 py-1.5 text-xs transition-all",
                isActive
                  ? "bg-gradient-to-r from-teal-100 to-cyan-50 dark:from-teal-900/40 dark:to-cyan-900/20 text-teal-700 dark:text-teal-300 font-semibold border border-teal-200/60 dark:border-teal-800/50"
                  : "text-slate-500 dark:text-slate-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 hover:text-teal-600 dark:hover:text-teal-400"
              )}
            >
              <Icon size={13} className="flex-shrink-0" />
              <span className="flex-1">{label}</span>
              {badge !== undefined && (
                <span className="bg-red-500 text-white text-[9px] rounded-full px-1.5 min-w-[16px] text-center">
                  {badge}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Status footer ──────────────────────────────────────────── */}
      <div className="px-4 py-3 border-t border-teal-100/60 dark:border-teal-900/30 space-y-1.5">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              wsConnected ? "bg-emerald-400 shadow-sm shadow-emerald-300" : "bg-slate-300 dark:bg-slate-600"
            )}
          />
          <span className="text-[10px] text-slate-400 dark:text-slate-500">
            {wsConnected ? "Live" : "Connecting…"}
          </span>
        </div>
        {isGuest && (
          <div className="text-[10px] text-blue-500 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-900 rounded-lg px-2 py-1 text-center">
            Guest · read-only
          </div>
        )}
      </div>
    </aside>
  );
}
