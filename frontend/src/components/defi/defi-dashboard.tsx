"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import useSWR from "swr";
import {
  Bar,
  BarChart,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ExternalLink,
  FileText,
  Radio,
  Shield,
  TrendingUp,
  Users,
  Wallet,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CasperDashboard } from "@/lib/api";

type DeFiView = "portfolio" | "yield" | "consensus" | "reputation" | "transactions" | "threats";

const TABS: { view: DeFiView; label: string; href: string; icon: LucideIcon }[] = [
  { view: "portfolio", label: "Portfolio", href: "/defi/portfolio", icon: Wallet },
  { view: "yield", label: "Yield", href: "/defi/yield-monitor", icon: TrendingUp },
  { view: "consensus", label: "Consensus", href: "/defi/swarm-consensus", icon: Users },
  { view: "reputation", label: "Reputation", href: "/defi/reputation", icon: Shield },
  { view: "transactions", label: "Transactions", href: "/defi/transactions", icon: FileText },
  { view: "threats", label: "Threat Radar", href: "/defi/threat-radar", icon: Radio },
];

const COLORS = ["#14b8a6", "#f97316", "#0ea5e9", "#8b5cf6", "#22c55e"];

export function DeFiDashboard({ view }: { view: DeFiView }) {
  const pathname = usePathname();
  const { data, error } = useSWR<CasperDashboard>("casper-dashboard", () => api.casperDashboard(), {
    refreshInterval: 5000,
  });

  if (!data) {
    return (
      <div className="max-w-7xl mx-auto space-y-4">
        <Header mode="loading" />
        <div className="rounded-xl border border-teal-100 dark:border-teal-900/30 bg-white/70 dark:bg-white/5 p-8 text-sm text-slate-500 dark:text-slate-400">
          {error ? "Casper DeFi API is offline." : "Loading Casper DeFi telemetry..."}
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-5">
      <Header mode={`${data.network.network ?? "testnet"} / ${data.network.mode ?? "demo"}`} />
      <div className="flex flex-wrap gap-2">
        {TABS.map(({ view: tabView, label, href, icon: Icon }) => {
          const active = view === tabView || pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-xs font-medium transition-colors",
                active
                  ? "border-teal-200 bg-teal-50 text-teal-700 dark:border-teal-800 dark:bg-teal-900/30 dark:text-teal-300"
                  : "border-slate-200 bg-white/60 text-slate-500 hover:border-teal-200 hover:text-teal-600 dark:border-slate-800 dark:bg-white/5 dark:text-slate-400"
              )}
            >
              <Icon size={14} />
              {label}
            </Link>
          );
        })}
      </div>

      {view === "portfolio" && <PortfolioView data={data} />}
      {view === "yield" && <YieldView data={data} />}
      {view === "consensus" && <ConsensusView data={data} />}
      {view === "reputation" && <ReputationView data={data} />}
      {view === "transactions" && <TransactionsView data={data} />}
      {view === "threats" && <ThreatView data={data} />}
    </div>
  );
}

function Header({ mode }: { mode: string }) {
  return (
    <div className="rounded-xl border border-teal-100 dark:border-teal-900/30 bg-white/75 dark:bg-white/5 p-5 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-gradient-to-br from-orange-400 to-teal-400 p-2 text-white">
            <Activity size={18} />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-slate-800 dark:text-slate-100">Casper DeFi Swarm</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">Treasury, quorum, reputation, and KAVACHA radar</p>
          </div>
        </div>
        <div className="rounded-lg border border-teal-100 bg-teal-50 px-3 py-1.5 text-xs font-mono text-teal-700 dark:border-teal-900 dark:bg-teal-900/20 dark:text-teal-300">
          {mode}
        </div>
      </div>
    </div>
  );
}

function PortfolioView({ data }: { data: CasperDashboard }) {
  const pieData = data.portfolio.holdings.map((h) => ({ name: h.asset, value: h.value_usd }));
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <Metric label="Treasury TVL" value={usd(data.portfolio.total_value_usd)} />
        <Metric label="24h P&L" value={`${data.portfolio.pnl_24h_pct.toFixed(2)}%`} />
        <Metric label="Risk Score" value={data.portfolio.risk_score.toFixed(2)} />
        <Metric label="Wallets" value={data.portfolio.wallets.length.toString()} />
      </div>
      <div className="grid lg:grid-cols-2 gap-4">
        <Panel title="Allocation">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={92} paddingAngle={3}>
                {pieData.map((_, index) => <Cell key={index} fill={COLORS[index % COLORS.length]} />)}
              </Pie>
              <Tooltip formatter={(value: number) => usd(value)} />
            </PieChart>
          </ResponsiveContainer>
        </Panel>
        <Panel title="Holdings">
          <div className="space-y-2">
            {data.portfolio.holdings.map((holding) => (
              <div key={holding.asset} className="grid grid-cols-[1fr_auto_auto] gap-3 rounded-lg border border-slate-100 bg-white/70 p-3 text-xs dark:border-slate-800 dark:bg-white/5">
                <span className="font-medium text-slate-700 dark:text-slate-200">{holding.asset}</span>
                <span className="font-mono text-slate-500">{usd(holding.value_usd)}</span>
                <span className="font-mono text-teal-600 dark:text-teal-300">{holding.allocation_pct.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}

function YieldView({ data }: { data: CasperDashboard }) {
  return (
    <div className="grid lg:grid-cols-[1.2fr_0.8fr] gap-4">
      <Panel title="APY Monitor">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.yields}>
            <XAxis dataKey="pool" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="apy_current" fill="#14b8a6" radius={[4, 4, 0, 0]} />
            <Bar dataKey="apy_7d_avg" fill="#f97316" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </Panel>
      <Panel title="Pools">
        <div className="space-y-2">
          {data.yields.map((pool) => (
            <div key={pool.pool} className="rounded-lg border border-slate-100 bg-white/70 p-3 text-xs dark:border-slate-800 dark:bg-white/5">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-700 dark:text-slate-200">{pool.pool}</span>
                <span className={cn("rounded px-2 py-0.5 font-medium", pool.status === "watch" ? "bg-amber-50 text-amber-700" : "bg-emerald-50 text-emerald-700")}>
                  {pool.status}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-slate-500">
                <span>{pool.apy_current.toFixed(1)}% APY</span>
                <span>{usd(pool.tvl_usd)} TVL</span>
                <span>{pool.slippage_bps} bps</span>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function ConsensusView({ data }: { data: CasperDashboard }) {
  const proposal = data.consensus;
  return (
    <div className="space-y-4">
      <Panel title={`Proposal ${proposal.proposal_id}`}>
        <div className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-base font-semibold text-slate-800 dark:text-slate-100">{proposal.title}</div>
              <div className="mt-1 text-xs text-slate-500">Quorum {proposal.quorum_votes}/{proposal.required_votes} · threshold {(proposal.threshold * 100).toFixed(0)}%</div>
            </div>
            <ExplorerLink href={proposal.explorer_url} />
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div className="h-full bg-teal-500" style={{ width: `${proposal.approval_ratio * 100}%` }} />
          </div>
        </div>
      </Panel>
      <div className="grid md:grid-cols-2 xl:grid-cols-4 gap-3">
        {proposal.votes.map((vote) => (
          <div key={vote.agent_id} className="rounded-xl border border-slate-100 bg-white/75 p-4 shadow-sm dark:border-slate-800 dark:bg-white/5">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{vote.role}</div>
              <span className={cn("rounded px-2 py-0.5 text-xs font-semibold", vote.vote === "approve" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700")}>
                {vote.vote}
              </span>
            </div>
            <p className="mt-3 text-xs leading-5 text-slate-600 dark:text-slate-300">{vote.rationale}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ReputationView({ data }: { data: CasperDashboard }) {
  return (
    <div className="grid lg:grid-cols-[1fr_1fr] gap-4">
      <Panel title="Trust Scores">
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={data.reputation.agents}>
            <XAxis dataKey="role" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} domain={[650, 850]} />
            <Tooltip />
            <Line type="monotone" dataKey="score" stroke="#14b8a6" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </Panel>
      <Panel title="On-chain Ledger">
        <div className="mb-3 rounded-lg bg-teal-50 px-3 py-2 text-xs font-mono text-teal-700 dark:bg-teal-900/20 dark:text-teal-300">
          {data.reputation.on_chain_anchor}
        </div>
        <div className="space-y-2">
          {data.reputation.agents.map((agent) => (
            <div key={agent.agent_id} className="grid grid-cols-[1fr_auto_auto] gap-3 rounded-lg border border-slate-100 bg-white/70 p-3 text-xs dark:border-slate-800 dark:bg-white/5">
              <span className="font-medium text-slate-700 dark:text-slate-200">{agent.agent_id}</span>
              <span className="font-mono text-slate-500">{agent.score}</span>
              <span className={cn("font-semibold", agent.trend === "up" ? "text-emerald-600" : "text-amber-600")}>{agent.trend}</span>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function TransactionsView({ data }: { data: CasperDashboard }) {
  return (
    <Panel title="Casper Deploy Log">
      <div className="space-y-2">
        {data.transactions.map((tx) => (
          <div key={tx.deploy_hash} className="grid gap-2 rounded-lg border border-slate-100 bg-white/70 p-3 text-xs dark:border-slate-800 dark:bg-white/5 md:grid-cols-[1fr_auto_auto]">
            <div>
              <div className="font-mono font-semibold text-slate-700 dark:text-slate-200">{tx.deploy_hash}</div>
              <div className="mt-1 text-slate-500">{tx.type} · {tx.agent_id}</div>
            </div>
            <div className="font-mono text-slate-500">{motes(tx.fee_motes)} fee</div>
            <ExplorerLink href={tx.explorer_url} />
          </div>
        ))}
      </div>
    </Panel>
  );
}

function ThreatView({ data }: { data: CasperDashboard }) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <Metric label="Open Threats" value={data.threats.length.toString()} />
        <Metric label="Critical" value={data.threats.filter((t) => t.severity_label === "critical").length.toString()} />
        <Metric label="Max Severity" value={(Math.max(...data.threats.map((t) => t.severity), 0) * 100).toFixed(0)} />
      </div>
      <Panel title="Threat Radar">
        <div className="space-y-2">
          {data.threats.map((threat) => (
            <div key={threat.threat_id} className="flex items-start gap-3 rounded-lg border border-slate-100 bg-white/70 p-3 text-xs dark:border-slate-800 dark:bg-white/5">
              <AlertTriangle size={15} className={threat.severity_label === "critical" ? "text-red-500" : "text-amber-500"} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-slate-700 dark:text-slate-200">{threat.type.replace(/_/g, " ")}</span>
                  <span className="font-mono text-slate-400">{threat.target}</span>
                  <span className="rounded bg-red-50 px-2 py-0.5 font-semibold text-red-700">{threat.severity_label}</span>
                </div>
                <p className="mt-1 text-slate-500 dark:text-slate-400">{threat.summary}</p>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-teal-100 bg-white/75 p-5 shadow-sm dark:border-teal-900/30 dark:bg-white/5">
      <div className="mb-4 text-sm font-semibold text-slate-800 dark:text-slate-100">{title}</div>
      {children}
    </section>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-teal-100 bg-white/75 p-4 shadow-sm dark:border-teal-900/30 dark:bg-white/5">
      <div className="text-xs text-slate-500 dark:text-slate-400">{label}</div>
      <div className="mt-1 text-xl font-bold font-mono text-slate-800 dark:text-slate-100">{value}</div>
    </div>
  );
}

function ExplorerLink({ href }: { href: string }) {
  return (
    <a href={href} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 rounded-lg border border-teal-100 px-2 py-1 text-xs font-medium text-teal-700 hover:bg-teal-50 dark:border-teal-900 dark:text-teal-300">
      Explorer <ExternalLink size={12} />
    </a>
  );
}

function usd(value: number) {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(value);
}

function motes(value: number) {
  return `${(value / 1_000_000_000).toFixed(4)} CSPR`;
}
