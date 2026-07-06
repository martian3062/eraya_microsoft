# ERAYA Casper — 13-Slide Deck

### Casper Agentic Buildathon 2026 · Qualification Round · Casper Innovation Track

> Team ERAYA · Team Lead: Pardeep Singh · sandhupardeep300@gmail.com
> Live: http://35.255.196.78/eraya · Open-source on GitHub

---

## Slide 1 — Title / Cover

**ERAYA Casper — Self-Healing Agentic DeFi Treasury Swarm**

- A production, **live** agentic system at the convergence of **Agentic AI × DeFi × RWA** on Casper.
- *Quorum before execution · KAVACHA before damage · x402 inside the agent economy.*
- Team ERAYA · Pardeep Singh · Casper Agentic Buildathon 2026 · Casper Innovation Track
- Live demo: **http://35.255.196.78/eraya**

---

## Slide 2 — The Problem

**DeFi does not fail politely.**

- Treasuries are run by humans or single "trade bots" — both break under adversarial, real-money conditions.
- On-chain systems punish **missing failure paths** with irreversible loss, not just a bad log line.
- Most agent demos optimise the happy path; none prove what happens when a fix itself fails.
- No on-chain agent identity, no economic signal for useful agent work, no adversarial review before high-stakes moves.

---

## Slide 3 — The Solution

**ERAYA turns a DeFi treasury into an immune system.**

- Four specialised AI agents **share context, vote (quorum) on high-stakes moves, and self-heal** instead of failing closed.
- If a remediation fails, the swarm **re-plans and recovers** — a real self-healing loop, not a script.
- Security-first by design: **KAVACHA** blocks unsafe actions and injection before damage.
- Agent economy: **x402** prices inter-agent work; reputation is anchored on Casper.

---

## Slide 4 — How It Works (4 Archetypes)

**Perceiver → Planner → Recoverer → Guardian, over an A2A bus.**

- **Perceiver** — reads Casper DeFi signals + risk features (TabPFN 3 tabular scoring).
- **Planner** — LLM cascade (Groq → Kimi → local HF) generates risk-adjusted rebalance actions.
- **Recoverer** — keeps rollback/retry paths ready; drives the self-healing reroute.
- **Guardian (KAVACHA)** — blocks unsafe actions, verifies A2A identity, writes signed audit.
- **3-tier cascade:** GPU/LLM → CPU models (TabPFN, XGBoost) → deterministic rules — never fails silently.

---

## Slide 5 — Architecture

**Product, swarm, and Casper layer in one deployed loop.**

- **Frontend:** Next.js console — DeFi portfolio · threat radar · swarm-consensus UI.
- **Backend:** Django + Channels — REST/WebSocket, audit log, domain registry (daphne on the VM).
- **Swarm core:** Perceiver · Planner · Recoverer · Guardian, coordinated via **HMAC-signed A2A** + **ErayaGraph** shared memory (Pinecone-backed).
- **Casper layer:** MCP facades · CSPR.click wallet · x402 + reputation.
- **Observability:** OpenTelemetry traces on every cascade tier.

---

## Slide 6 — Casper Integration (Track-Critical)

**Casper-native, not Casper-adjacent.**

- **`casper_defi` domain adapter** — live CSPR.cloud / CSPR.trade-shaped telemetry: pool TVL, APY, gas, slippage, liquidity depth, governance quorum, validator uptime, mempool.
- **x402-aware A2A** — paid inter-agent requests via `X402EnabledBus`.
- **CSPR.click wallet** + **Casper MCP** facades — demo-safe today, provider URLs ready to go live.
- **Odra contracts (roadmap):** agent registry, treasury, governance, reputation on Casper testnet.
- **Reputation batches** shaped for on-chain anchoring.

---

## Slide 7 — Agentic AI Stack

**A priced, audited, voting swarm — not a single DEX-calling agent.**

- **LLM cascade:** Groq (`llama-3.3-70b`) → Kimi (long-context) → local Hugging Face fallback.
- **Risk brain:** **TabPFN 3** tabular foundation model (live, hosted) scores DeFi risk with zero training.
- **Memory / RAG:** Pinecone vector store (ErayaGraph); Firecrawl web ingestion.
- **Multilingual:** Sarvam AI. **Orchestration:** LangGraph swarm graph.
- **Every provider is a graceful-fallback facade** — the demo never breaks if a key/service is down.

---

## Slide 8 — Security-First (KAVACHA)

**Threats hunted before a bad deploy lands.**

- **Injection kill-shot:** operator/agent inputs scanned; unsafe actions **BLOCKED** with a signed audit trail. (Live: verdict `BLOCKED`, rule `R003`, full timeline.)
- **A2A identity defense:** forged agent messages rejected via HMAC signature check — the same function the live WebSocket path uses.
- **Quorum before execution:** high-stakes DeFi moves need swarm consensus, not one agent's call.
- **Proactive threat scanner:** mempool, liquidity, and governance risk.

---

## Slide 9 — Live Proof (Working Today)

**The `/eraya` deployment is serving the Casper DeFi console right now.**

- Public: `http://35.255.196.78/eraya` → **200**; DeFi route + dashboard API → **200**.
- Live metrics: treasury **$820K**, APY **12.86%**, governance quorum **47%**, validator uptime **99.2%**, risk score computed by TabPFN.
- KAVACHA attack-sim, swarm status, and A2A feed all respond with real data.
- Runs on real provider keys (Groq, Kimi, Pinecone, Firecrawl, TabPFN, Sarvam) — **production, not slideware**.

---

## Slide 10 — DeFi + RWA + AI Convergence

**One engine, three of Casper's priorities.**

- **DeFi:** autonomous treasury rebalance, yield monitoring, slippage/liquidity-aware execution.
- **RWA-ready:** the swarm is domain-agnostic — a 3-method adapter plugs in **any** real-world asset stream (already proven across 5G, cloud, ICU domains) without touching the agents.
- **Agentic AI:** self-healing, quorum, priced agent economy — the "how do agents act safely with real money" story.
- Positions ERAYA squarely at **Casper's DeFi × RWA × AI** intersection.

---

## Slide 11 — Why We Win

**Defined failure behaviour is our moat.**

- Only entry where **every agent has a defined failure path** — the swarm never fully stops.
- **Live, open-source, production-ready** — judges can hit the URL now.
- **Real** LLM planning + **real** TabPFN risk + **real** Casper telemetry — no stubs on the critical path.
- Two hard problems solved together: **agent safety** (KAVACHA) + **agent economics** (x402 + reputation).

---

## Slide 12 — Roadmap

**From demo-safe facades to live testnet execution.**

1. **Wire live providers** — CSPR.cloud, Casper MCP, CSPR.trade MCP, CSPR.click; keep deterministic fallback for stage demos.
2. **Deploy Odra contracts** — agent registry, treasury, governance, reputation on Casper testnet (explorer links).
3. **Record real outcomes** — flush x402 payments, quorum votes, and KAVACHA vetoes to chain-visible transactions.
4. **Scale RWA adapters** — onboard a real-world asset feed end-to-end.

---

## Slide 13 — Team, Ask & Links

**Team ERAYA**

- **Team Lead:** Pardeep Singh — sandhupardeep300@gmail.com
- **Live demo:** http://35.255.196.78/eraya
- **Repository:** github.com/martian3062/eraya_microsoft (branch `caspr`) — open-source
- **The ask:** vote **ERAYA Casper** on **CSPR.fans** to advance to the Final Round — a live, self-healing agentic DeFi treasury built Casper-native.

---

*ERAYA Casper · Self-Healing Agentic DeFi Treasury Swarm · Casper Agentic Buildathon 2026*
