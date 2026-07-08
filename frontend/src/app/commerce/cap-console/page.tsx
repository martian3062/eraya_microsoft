"use client";
import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  ShoppingCart, ArrowUpRight, ArrowDownLeft, Shield, Loader2,
  BadgeCheck, Skull, Link2,
} from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Step { step: string; ok: boolean; detail: string; score?: number; }
interface Proof { result_hash: string; attestation: string; audit_key_id: string; record_id?: string; }
interface Scan { verdict: string; injection_score: number; rule_fired: string | null; audit_id: string; timeline: Step[]; proof: Proof; }
interface Status { online: boolean; demo_mode: boolean; agent: string; did: string; wallet: string; network: string; services: { id: string; name: string; track: string; price_usdc: number }[]; }
interface Earnings { earned_usdc: number; pts: number; spent_usdc: number; demo_mode: boolean; }
interface Order { order_id: string; direction: string; service: string; status: string; verdict: string; usdc: number; pts_delta: number; }

export default function CapConsolePage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [earn, setEarn] = useState<Earnings | null>(null);
  const [orders, setOrders] = useState<Order[]>([]);
  const [proof, setProof] = useState<Proof | null>(null);
  const [sell, setSell] = useState<Scan | null>(null);
  const [buy, setBuy] = useState<{ scan: Scan; approved: boolean; preview: string; did: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [s, e, o] = await Promise.all([
        fetch(`${API_BASE}/api/commerce/cap/status/`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/commerce/cap/earnings/`).then((r) => r.json()).catch(() => null),
        fetch(`${API_BASE}/api/commerce/cap/orders/`).then((r) => r.json()).catch(() => ({ orders: [] })),
      ]);
      if (s) setStatus(s);
      if (e) setEarn(e);
      setOrders(o?.orders ?? []);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => { refresh(); const t = setInterval(refresh, 10000); return () => clearInterval(t); }, [refresh]);

  async function runSell() {
    setBusy("sell"); setSell(null);
    try {
      const d = await fetch(`${API_BASE}/api/commerce/cap/order/`, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: "{}",
      }).then((r) => r.json());
      setSell(d.deliverable); setProof(d.deliverable?.proof ?? null);
    } catch { /* ignore */ } finally { setBusy(null); refresh(); }
  }

  async function runBuy(poison: boolean) {
    setBusy(poison ? "buyp" : "buy"); setBuy(null);
    try {
      const d = await fetch(`${API_BASE}/api/commerce/cap/hire/`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ poison }),
      }).then((r) => r.json());
      setBuy({ scan: d.scan, approved: d.approved, preview: d.delivery_preview, did: d.order?.provider_did });
      setProof(d.scan?.proof ?? null);
    } catch { /* ignore */ } finally { setBusy(null); refresh(); }
  }

  const blocked = (v: string) => /BLOCK|QUAR|disput/i.test(v || "");

  return (
    <div className="max-w-6xl mx-auto space-y-5">
      <div>
        <h1 className="text-base font-semibold flex items-center gap-2 text-slate-800 dark:text-slate-100">
          <ShoppingCart size={15} className="text-orange-500" /> ERAYA × CAP — Commerce Console
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
          KAVACHA as a paid, CAP-callable trust service on CROO (Base · USDC). ERAYA sells verification —
          and dogfoods it on every external agent it hires.
        </p>
      </div>

      {/* Status + earnings */}
      <div className="rounded-xl border border-orange-100 dark:border-orange-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5 space-y-3">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
            {status ? <>agent <b className="text-slate-700 dark:text-slate-200">{status.agent}</b> · {status.did} · {status.wallet.slice(0, 16)}…</> : "connecting…"}
          </div>
          <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded",
            status?.demo_mode ? "bg-amber-100 dark:bg-amber-900/40 text-amber-600 dark:text-amber-400"
              : "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400")}>
            {status ? (status.demo_mode ? "DEMO MODE" : "LIVE · BASE") : "…"}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Kpi label="Earned (USDC)" value={`$${earn?.earned_usdc ?? 0}`} />
          <Kpi label="PTS / Merit" value={earn?.pts ?? 0} />
          <Kpi label="Spent (USDC)" value={`$${earn?.spent_usdc ?? 0}`} />
          <Kpi label="Services" value={status?.services?.length ?? 0} />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* SELL */}
        <Card title="SELL — external agent hires KAVACHA Scan" icon={<ArrowUpRight size={14} className="text-orange-500" />}>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            An inbound CAP order routes into ERAYA&apos;s attack-sim pipeline. CAP settles only on verified
            delivery — the Guardian&apos;s HMAC audit record <i>is</i> the proof.
          </p>
          <button onClick={runSell} disabled={busy === "sell"}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 disabled:opacity-50 text-white text-xs font-medium rounded-lg py-2 shadow-sm">
            {busy === "sell" ? <Loader2 size={13} className="animate-spin" /> : <ArrowUpRight size={13} />}
            Simulate inbound order (injection payload)
          </button>
          {sell && (
            <div className="pt-2 space-y-1.5">
              <Verdict v={sell.verdict} note={`rule ${sell.rule_fired ?? "—"} · score ${sell.injection_score}`} />
              <Timeline steps={sell.timeline} />
            </div>
          )}
        </Card>

        {/* BUY */}
        <Card title="BUY + DOGFOOD — ERAYA hires an external agent" icon={<ArrowDownLeft size={14} className="text-emerald-500" />}>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            The Planner hires an external CAP agent; its delivery is vetted by ERAYA&apos;s own KAVACHA before
            the swarm trusts it. <i>The product we sell is the product we use on ourselves.</i>
          </p>
          <div className="flex gap-2">
            <button onClick={() => runBuy(false)} disabled={busy === "buy"}
              className="flex-1 flex items-center justify-center gap-2 bg-emerald-50 dark:bg-emerald-900/20 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 border border-emerald-200 dark:border-emerald-800 disabled:opacity-50 text-emerald-600 dark:text-emerald-400 text-xs font-medium rounded-lg py-2">
              {busy === "buy" ? <Loader2 size={12} className="animate-spin" /> : <BadgeCheck size={12} />} Hire (clean)
            </button>
            <button onClick={() => runBuy(true)} disabled={busy === "buyp"}
              className="flex-1 flex items-center justify-center gap-2 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/40 border border-red-200 dark:border-red-800 disabled:opacity-50 text-red-600 dark:text-red-400 text-xs font-medium rounded-lg py-2">
              {busy === "buyp" ? <Loader2 size={12} className="animate-spin" /> : <Skull size={12} />} Hire (poisoned)
            </button>
          </div>
          {buy && (
            <div className="pt-2 space-y-1.5">
              <div className="text-[10px] font-mono text-slate-400 dark:text-slate-500">hired {buy.did}</div>
              <div className="text-[11px] text-slate-500 dark:text-slate-400">delivery: “{buy.preview.slice(0, 120)}…”</div>
              <Verdict v={buy.scan.verdict} note={buy.approved ? "swarm executed ✓" : "swarm vetoed by Guardian ✕"} />
              <Timeline steps={buy.scan.timeline} />
            </div>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Proof */}
        <Card title="Delivery Proof — CAP DeliverOrder attestation" icon={<Link2 size={14} className="text-orange-500" />}>
          {proof ? (
            <div className="space-y-2 text-[11px] font-mono break-all">
              <div><span className="text-slate-400">result_hash</span><div className="text-orange-600 dark:text-orange-400">{proof.result_hash}</div></div>
              <div><span className="text-slate-400">attestation · HMAC-SHA256 (ERAYA_AUDIT_KEY)</span><div className="text-slate-600 dark:text-slate-300">{proof.attestation.slice(0, 72)}…</div></div>
              <div><span className="text-slate-400">audit_key_id</span> {proof.audit_key_id} · <span className="text-slate-400">record</span> {(proof.record_id ?? "").slice(0, 12)}</div>
            </div>
          ) : <p className="text-xs text-slate-500 dark:text-slate-400">Run a service — the {"{result_hash, execution_log, HMAC attestation}"} appears here. Exactly what CAP demands before settling.</p>}
        </Card>

        {/* Orders */}
        <Card title="Order Ledger — Negotiate→Lock→Deliver→Clear" icon={<Shield size={14} className="text-orange-500" />}>
          <div className="max-h-72 overflow-y-auto space-y-1.5">
            {orders.length === 0 && <p className="text-xs text-slate-500 dark:text-slate-400">No orders yet.</p>}
            {orders.map((o) => (
              <div key={o.order_id} className="flex items-center justify-between text-[11px] rounded-lg border border-slate-200 dark:border-slate-700 bg-white/50 dark:bg-white/5 px-2.5 py-1.5">
                <span className="flex items-center gap-1.5 min-w-0">
                  <span className={cn("font-bold", o.direction === "sell" ? "text-orange-500" : "text-emerald-500")}>
                    {o.direction === "sell" ? "↑ sell" : "↓ buy"}
                  </span>
                  <span className="text-slate-500 dark:text-slate-400 truncate">{o.service}</span>
                  <span className={cn("text-[10px] px-1.5 py-0.5 rounded",
                    blocked(o.verdict + o.status) ? "bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400"
                      : "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400")}>
                    {o.verdict || o.status}
                  </span>
                </span>
                <span className={cn(o.direction === "sell" ? "text-orange-500" : "text-emerald-500")}>
                  {o.usdc ? `$${o.usdc}${o.pts_delta ? ` · +${o.pts_delta}pts` : ""}` : o.status}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 dark:border-slate-700 bg-white/50 dark:bg-white/5 p-3">
      <div className="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider">{label}</div>
      <div className="text-lg font-bold text-slate-800 dark:text-slate-100">{value}</div>
    </div>
  );
}

function Card({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-orange-100 dark:border-orange-900/30 bg-white/70 dark:bg-white/5 backdrop-blur-sm shadow-sm p-5 space-y-3">
      <div className="flex items-center gap-2">{icon}<span className="text-sm font-medium text-slate-800 dark:text-slate-100">{title}</span></div>
      {children}
    </div>
  );
}

function Verdict({ v, note }: { v: string; note: string }) {
  const bad = /BLOCK|QUAR|veto/i.test(v + note);
  return (
    <div className="flex items-center gap-2">
      <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded",
        bad ? "bg-red-100 dark:bg-red-900/40 text-red-600 dark:text-red-400"
          : "bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400")}>{v}</span>
      <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">{note}</span>
    </div>
  );
}

function Timeline({ steps }: { steps: Step[] }) {
  return (
    <div className="space-y-1">
      {steps?.map((s, i) => (
        <div key={i} className="flex items-start gap-2 text-[11px]">
          <span className={cn("mt-0.5", s.ok ? "text-emerald-500" : "text-red-500")}>●</span>
          <span className="min-w-0"><span className="font-mono text-slate-600 dark:text-slate-300">{s.step}</span>
            <span className="text-slate-500 dark:text-slate-400 ml-1.5 break-all">{s.detail}</span>
            {s.score !== undefined && <span className="ml-1.5 text-[10px] text-orange-500">score {s.score}</span>}
          </span>
        </div>
      ))}
    </div>
  );
}
