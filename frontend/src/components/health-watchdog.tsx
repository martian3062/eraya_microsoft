"use client";
/**
 * HealthWatchdog — mounts once in AppShell, invisible.
 * Fires at 30 s (ping) and 60 s (comprehensive check) intervals.
 * Pushes results to both the A2A feed and the health store.
 */
import { useEffect, useRef } from "react";
import { useErayaStore } from "@/store";
import { useHealthStore } from "@/store/health";

const DOMAINS = ["5g", "cloud", "icu", "network"] as const;
type Domain = typeof DOMAINS[number];

const ARCHETYPES = ["perceiver", "planner", "recoverer", "guardian"] as const;
type Arch = typeof ARCHETYPES[number];

function agentId(role: Arch, domain: Domain) {
  const d = domain === "network" ? "net" : domain;
  return `${role}-${d}-001`;
}

function ts() { return new Date().toISOString(); }
function uid() { return Math.random().toString(36).slice(2, 10); }

/* ── 30-second ping: guardian → planner quick heartbeat ─────────── */
function gen30sCheck(domain: Domain, warn: boolean) {
  const checker = agentId("guardian", domain);
  const target  = agentId("planner", domain);
  const latency = warn ? 380 + Math.floor(Math.random() * 120) : 15 + Math.floor(Math.random() * 40);
  const status  = warn ? "warning" as const : "ok" as const;

  return {
    pingEvent: {
      id: uid(), from: checker, to: target,
      type: "heartbeat", domain,
      timestamp: ts(),
      payload: { check: "30s-ping", expecting: "tier+latency" },
    },
    pongEvent: {
      id: uid(), from: target, to: checker,
      type: "heartbeat", domain,
      timestamp: ts(),
      payload: warn
        ? { status: "DEGRADED", tier: "MEDIUM", latency_ms: latency, note: "Tier 1 latency exceeded budget" }
        : { status: "OK", tier: "HEAVY", latency_ms: latency, error_rate: "0.1%" },
    },
    check: {
      id: uid(), timestamp: ts(), interval: "30s" as const, domain,
      checker, target, status,
      detail: warn
        ? `Planner latency ${latency}ms > 100ms budget — escalating to 60s check`
        : `Planner responsive · latency ${latency}ms · Tier HEAVY`,
      latency_ms: latency,
    },
  };
}

/* ── 60-second comprehensive check: guardian → all 3 peers ──────── */
function gen60sCheck(domain: Domain, warnArch: Arch | null) {
  const checker = agentId("guardian", domain);
  const peers: Arch[] = ["perceiver", "planner", "recoverer"];
  const events: ReturnType<typeof Object.create>[] = [];
  const checks: ReturnType<typeof Object.create>[] = [];

  for (const arch of peers) {
    const target = agentId(arch, domain);
    const warn = arch === warnArch;
    const latency = warn ? 410 + Math.floor(Math.random() * 90) : 12 + Math.floor(Math.random() * 60);
    const status: "ok" | "warning" | "healed" = warn ? "warning" : "ok";

    events.push({
      id: uid(), from: checker, to: target,
      type: "capability.query", domain, timestamp: ts(),
      payload: { check: "60s-health", scope: "full" },
    });

    const detail = warn
      ? buildWarnDetail(arch, latency)
      : buildOkDetail(arch, latency, domain);

    events.push({
      id: uid(), from: target, to: checker,
      type: warn ? "action.response" : "action.response", domain, timestamp: ts(),
      payload: warn
        ? { status: "WARNING", latency_ms: latency, issue: buildWarnDetail(arch, latency) }
        : { status: "NOMINAL", latency_ms: latency },
    });

    checks.push({
      id: uid(), timestamp: ts(), interval: "60s" as const, domain,
      checker, target, status,
      detail: warn ? buildWarnDetail(arch, latency) : detail,
      latency_ms: latency,
    });

    /* If warning → generate heal sequence */
    if (warn) {
      const recoverer = agentId("recoverer", domain);
      events.push({
        id: uid(), from: checker, to: recoverer,
        type: "action.request", domain, timestamp: ts(),
        payload: { action: "tier_downgrade", target, from_tier: "HEAVY", to_tier: "MEDIUM" },
      });
      const healLatency = 55 + Math.floor(Math.random() * 45);
      events.push({
        id: uid(), from: recoverer, to: checker,
        type: "action.response", domain, timestamp: ts(),
        payload: { ok: true, new_latency_ms: healLatency, action: "tier_downgrade", status: "HEALED" },
      });
      checks.push({
        id: uid(), timestamp: ts(), interval: "60s" as const, domain,
        checker: recoverer, target, status: "healed",
        detail: `Self-healed: downgraded to Tier 2 · latency now ${healLatency}ms · nominal`,
        latency_ms: healLatency,
      });
    }
  }

  return { events, checks };
}

function buildOkDetail(arch: Arch, latency: number, domain: Domain): string {
  const map: Record<Arch, string> = {
    perceiver: `Signal encoder active · anomaly detector: ARMED · latency ${latency}ms`,
    planner:   `Decision engine nominal · algo: cascade-ready · latency ${latency}ms`,
    recoverer: `Circuit breaker: CLOSED · fallback: armed · latency ${latency}ms`,
    guardian:  `Policy engine: active · rules R001-R003: loaded · latency ${latency}ms`,
  };
  return map[arch];
}

function buildWarnDetail(arch: Arch, latency: number): string {
  const map: Record<Arch, string> = {
    perceiver: `Encoder latency ${latency}ms — GPU context switch detected`,
    planner:   `Tier 1 latency ${latency}ms > 100ms budget — LLM backpressure`,
    recoverer: `Rollout latency ${latency}ms — replay buffer near capacity`,
    guardian:  `Policy eval ${latency}ms — OPA rule cache miss`,
  };
  return map[arch];
}

/* ── Component ───────────────────────────────────────────────────── */
export function HealthWatchdog() {
  const { pushA2AEvent } = useErayaStore();
  const { pushCheck } = useHealthStore();
  const tickRef = useRef(0);            // counts 30s ticks; every 2nd tick = 60s

  useEffect(() => {
    function run30s() {
      tickRef.current += 1;
      const domainIdx = (tickRef.current - 1) % DOMAINS.length;
      const domain = DOMAINS[domainIdx];

      /* ~15% chance of a warning on the 30s ping */
      const warn = Math.random() < 0.15;
      const { pingEvent, pongEvent, check } = gen30sCheck(domain, warn);

      pushA2AEvent(pingEvent);
      setTimeout(() => pushA2AEvent(pongEvent), 800);
      setTimeout(() => pushCheck(check), 900);

      /* On every 2nd tick (60s) do comprehensive check */
      if (tickRef.current % 2 === 0) {
        const compDomain = DOMAINS[(tickRef.current / 2 - 1) % DOMAINS.length];
        /* ~25% chance of a warning in the 60s check */
        const warnArch = Math.random() < 0.25
          ? (["perceiver", "planner", "recoverer"] as Arch[])[Math.floor(Math.random() * 3)]
          : null;
        const { events, checks } = gen60sCheck(compDomain, warnArch);
        let delay = 1200;
        for (const ev of events) {
          setTimeout(() => pushA2AEvent(ev), delay);
          delay += 600;
        }
        for (const ch of checks) {
          setTimeout(() => pushCheck(ch), delay);
          delay += 200;
        }
      }
    }

    /* Fire once after 3 s so the user sees activity on first load */
    const boot = setTimeout(() => { tickRef.current = 0; run30s(); }, 3000);
    const interval = setInterval(run30s, 30_000);

    return () => {
      clearTimeout(boot);
      clearInterval(interval);
    };
  }, [pushA2AEvent, pushCheck]);

  return null;
}
