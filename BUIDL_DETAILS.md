# ERAYA — Self-Healing Agentic Treasury on Casper

**A five-agent AI swarm that watches, trades, defends and repairs an on-chain Casper treasury — autonomously, 24/7, with every decision signed and auditable.**

Live: **https://eraya.online** · Guest login works instantly (no wallet needed).

---

## The problem

Autonomous agents are being handed real money. Almost none of them are safe to hand money to.

A single LLM agent with a private key is one prompt injection away from draining a treasury. There is no second opinion, no policy layer, no audit trail, and no way to recover when it goes wrong. "Trust me, it's an AI" is not a security model.

## What ERAYA does

ERAYA replaces the single agent with a **swarm of five specialists that argue with each other before anything touches the chain** — and puts the rules they must obey into Casper smart contracts, where no agent can rewrite them.

| Agent | Model / vendor | Speaks every | Job |
|---|---|---|---|
| **Perceiver** | Groq — Llama-4-Scout-17B | 5s | Reads the tape: prices, mempool, telemetry |
| **Recoverer** | Groq — Llama-3.1-8B | 8s | Stages rollback and retry paths |
| **Planner** | Groq — Llama-3.3-70B | 10s | Commits to the strategy call |
| **Guardian** | OpenAI — GPT-4o-mini | 15s | Policy review, holds veto power |
| **Critic** | Kimi / Moonshot | 30s | Independent outside opinion, prices the unpriced risk |

Deliberately **multi-vendor**: Groq, OpenAI and Moonshot. One poisoned model cannot capture the swarm, because the agent that reviews it runs on a different company's weights. Each vendor speaks at its own cadence, so the room has real tempo instead of a lockstep round-robin.

---

## The seven surfaces

### 1. Chatbook (A2A)
The swarm's live group chat. Agents talk to each other in plain language over an agent-to-agent bus, every message signed and tagged with its provider and model. This is not a transcript replay — open it and the agents are reasoning in real time about whatever the treasury is doing right now.

### 2. KAVACHA — the defense layer
*Kavacha* (कवच) means "armour". It merges three defenses into one screen:
- **Injection Sentinel** — scores every inbound instruction for prompt-injection before an agent can act on it
- **Policy Auditor** — checks the proposed action against on-chain policy; violations are blocked, not warned about
- **Audit Signer** — HMAC-signs every decision record, so the log is tamper-evident after the fact

Run the attack simulator on the live site and watch a poisoned payload get scored, blocked, and signed in front of you.

### 3. Quant Desk — autonomous trading
A weighted ensemble, not a single indicator:

| Signal | Weight |
|---|---|
| SMA 9/26 crossover | 27% |
| Momentum | 23% |
| RSI-14 | 22% |
| Bollinger bands | 18% |
| **Crowd emotion (Fear & Greed)** | 10% — *contrarian* |

The crowd-emotion input is the interesting one: when the market is maximally fearful, the ensemble leans **in**, not out. Scalper cadence is derived from the user's own risk setting — risk 1 ticks every 30 seconds, risk 10 every 5 — with live P&L, session metrics, and forward projections. You set your own CSPR stake and watch the agents work it.

### 4. Wallet — real Casper, real transfers
Not a mock. Real balances read from the Casper 2.0 testnet JSON-RPC, real transfers signed with `casper-client put-transaction`. **Treasury Autopay** is the showcase: Guardian writes the policy, Recoverer executes within it, and the transfer only lands if it satisfies the on-chain `TradePolicy` contract.

### 5. x402 — agents paying agents
ERAYA sells its live quant signal and market data to external agents over **x402** (HTTP 402 Payment Required). The facilitator is real: a proof arrives as `casper:<payer>:<amount>:<tx_hash>`, and ERAYA settles it directly against the Casper node — pulling the transaction, confirming it executed without error on `casper-test`, and walking its transfers for one that genuinely moved ≥ the asking price to the receiver's account hash.

Forged hashes, failed transactions, transfers to the wrong account, short payments, replayed hashes, and proofs claimed by the wrong payer are all rejected. No third-party indexer is involved — the chain is the arbiter.

### 6. Casper as MCP tools
The swarm exposes Casper itself as an **MCP server**, so any MCP client — Claude Desktop, Copilot, another agent — can independently verify ERAYA's on-chain claims instead of taking the UI's word for them: `casper_chain_status`, `casper_balance`, `casper_transaction`, `casper_deployed_contracts`, `casper_account_hash`, `casper_signing_key_status`, `casper_x402_challenge`, `casper_x402_verify`.

That last pair matters: an external agent can mint a payment challenge and settle a proof entirely over MCP. Buying from the swarm is itself an agent-callable tool.

### 7. Voice
Talk to the swarm. Speech-to-text via Groq Whisper large-v3-turbo, replies spoken back through ElevenLabs. Say *"send 25 coins"* and the advisory copilot parses the intent, runs it past Guardian, and either executes or tells you why it refused.

---

## On-chain — Odra smart contracts (Rust → Wasm)

Two Odra contracts, **live on Casper testnet**, define the guarantees the swarm operates under:

| Contract | Package hash |
|---|---|
| **AgentRegistry** | [`hash-d2cf3bba…fe41`](https://testnet.cspr.live/contract-package/d2cf3bba6ca8470ffbda9f377897150338c2507dfd517072e4c6ba7a5df6fe41) |
| **TradePolicy** | [`hash-6f094573…da8f`](https://testnet.cspr.live/contract-package/6f0945738701c454919f090fca2044aec25b57d9977800fa8cf70f899a5eda8f) |

Deployed from `0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69`. The install transactions carry the four swarm archetypes being registered on-chain and the risk dial being set — all verifiable on cspr.live.

- **`AgentRegistry`** — the identity and trust registry. Which agents exist, what capabilities they hold, what trust tier they sit in. An unregistered agent has no standing in the swarm.
- **`TradePolicy`** — the spending constitution. Per-transaction caps, allowlists, quorum requirements. Enforced by the chain at execution time, so an agent that decides to ignore policy simply produces a transaction that fails.

This is the core thesis: **the AI proposes, the chain disposes.** Agents can be jailbroken. The Wasm cannot be sweet-talked.

---

## Architecture

```
Voice / Chat / Web ─┐
                    ▼
        ┌───────────────────────┐
        │  A2A Bus (signed)     │
        │  5 agents, 3 vendors  │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  KAVACHA              │
        │  injection · policy   │
        │  · HMAC audit         │
        └───────────┬───────────┘
                    ▼
        ┌───────────────────────┐
        │  Casper 2.0 testnet   │
        │  AgentRegistry        │
        │  TradePolicy (Odra)   │
        └───────────────────────┘
```

Every path to the chain goes through KAVACHA. There is no bypass.

## Tech stack

**Chain** — Casper 2.0 testnet · Odra 2.9 (Rust → Wasm) · native Casper Rust SDK (`casper-contract`) · pycspr (Python SDK, account-hash derivation + signing) · Casper 2.0 JSON-RPC · x402 facilitator · MCP server exposing Casper as agent tools
**Backend** — Django 5.2 · Django REST Framework · Channels / Daphne (ASGI, WebSockets)
**AI** — Groq (3-key failover), OpenAI GPT-4o-mini, Kimi/Moonshot, Groq Whisper STT, ElevenLabs TTS
**Frontend** — D3.js charts, GSAP motion, Three.js ambient layer, glassmorphic design system
**Security** — HMAC audit signing, session auth with role-scoped spend caps (guest 30 CSPR · account 100 · admin unlimited)
**Infra** — Cloudflare Tunnel, HTTPS on a custom domain

---

## Try it

1. Go to **https://eraya.online** and hit **Guest login** — 30 CSPR of testnet allowance, no wallet setup.
2. Open **Chatbook (A2A)** and watch five models from three vendors coordinate live.
3. Open **KAVACHA**, fire the attack simulator, and watch an injection get blocked and signed.
4. Open **Quant Desk**, set a stake and a risk level, hit start, and watch the ensemble trade with live P&L.
5. Open **Wallet** and move real testnet CSPR through the policy contract.

## What's genuinely working

Real Casper testnet transactions, signed and landed on chain. Two real Odra contracts installed on testnet, with the swarm's four archetypes registered on-chain. Five real models from three vendors reasoning in real time. Real Whisper transcription and real speech synthesis. No mocked responses, no canned transcripts, no fake balances.

**The pitch in one line:** everyone is racing to give agents money. ERAYA is the layer that makes that survivable.
