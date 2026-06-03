"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, Bot, Radio, Cloud, Activity,
  AlertTriangle, FileText, GitBranch, Settings, Shield,
} from "lucide-react";
import { useErayaStore } from "@/store";

const NAV = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  {
    label: "Agents", icon: Bot, children: [
      { label: "Perceiver", href: "/agents/perceiver" },
      { label: "Planner", href: "/agents/planner" },
      { label: "Recoverer", href: "/agents/recoverer" },
      { label: "Guardian", href: "/agents/guardian" },
    ],
  },
  {
    label: "Domains", icon: Activity, children: [
      { label: "5G Self-Healing", href: "/domains/5g" },
      { label: "Cloud Cost", href: "/domains/cloud" },
      { label: "ICU Monitoring", href: "/domains/icu" },
    ],
  },
  { label: "Context Graph", href: "/context-graph", icon: GitBranch },
  { label: "Incidents", href: "/incidents", icon: AlertTriangle },
  { label: "Audit Log", href: "/audit-log", icon: FileText },
  {
    label: "Security", icon: Shield, children: [
      { label: "Attack Console", href: "/security/attack-console" },
    ],
  },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { guardianAlerts, wsConnected } = useErayaStore();

  return (
    <aside className="w-56 flex-shrink-0 bg-[#111827] border-r border-[#1f2937] flex flex-col">
      {/* Logo */}
      <div className="px-4 py-5 border-b border-[#1f2937]">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center text-xs font-bold">
            E
          </div>
          <div>
            <div className="text-sm font-semibold tracking-wide">ERAYA</div>
            <div className="text-[10px] text-slate-500">Agent Swarm v0.1</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV.map((item) =>
          "children" in item ? (
            <NavGroup key={item.label} item={item} pathname={pathname} />
          ) : (
            <NavItem
              key={item.href}
              href={item.href!}
              label={item.label}
              icon={item.icon}
              active={pathname === item.href}
              badge={item.label === "Incidents" && guardianAlerts > 0 ? guardianAlerts : undefined}
            />
          )
        )}
      </nav>

      {/* WS status */}
      <div className="px-4 py-3 border-t border-[#1f2937] flex items-center gap-2">
        <div className={cn("w-2 h-2 rounded-full", wsConnected ? "bg-emerald-400" : "bg-slate-600")} />
        <span className="text-[11px] text-slate-500">
          {wsConnected ? "Live" : "Connecting…"}
        </span>
      </div>
    </aside>
  );
}

function NavGroup({ item, pathname }: { item: typeof NAV[number] & { children: { label: string; href: string }[] }; pathname: string }) {
  const Icon = item.icon;
  const active = item.children.some((c) => pathname.startsWith(c.href));

  return (
    <div>
      <div className={cn("flex items-center gap-2 px-3 py-2 text-xs font-medium text-slate-500 uppercase tracking-wider mt-2")}>
        <Icon size={13} />
        {item.label}
      </div>
      {item.children.map((child) => (
        <NavItem
          key={child.href}
          href={child.href}
          label={child.label}
          active={pathname === child.href}
          indent
        />
      ))}
    </div>
  );
}

function NavItem({
  href, label, icon: Icon, active, badge, indent,
}: {
  href: string; label: string; icon?: React.ElementType;
  active?: boolean; badge?: number; indent?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-2 rounded-md px-3 py-1.5 text-sm transition-colors",
        indent && "pl-7 text-xs",
        active
          ? "bg-indigo-600/20 text-indigo-300"
          : "text-slate-400 hover:bg-white/5 hover:text-slate-200"
      )}
    >
      {Icon && <Icon size={14} />}
      <span className="flex-1">{label}</span>
      {badge !== undefined && (
        <span className="ml-auto bg-red-600 text-white text-[10px] rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
          {badge}
        </span>
      )}
    </Link>
  );
}
