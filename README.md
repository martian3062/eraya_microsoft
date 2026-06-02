# ERAYA — Self-Healing Agent Swarm Framework

> **Microsoft Build AI Hackathon 2026 | Theme: Agent Swarms × Security**

> *Eraya (एरया) — Sanskrit: "the one that moves toward, navigates, adapts."*

[![Python](https://img.shields.io/badge/Python-3.10-blue)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2-green)](https://djangoproject.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-black)](https://nextjs.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.11%2Bcu128-red)](https://pytorch.org)
[![CUDA](https://img.shields.io/badge/CUDA-12.8-76B900)](https://developer.nvidia.com/cuda-toolkit)

---

## What is Eraya?

Eraya is a **domain-agnostic 4-archetype agent swarm** that self-heals real-world adaptive systems — 5G networks, hospital ICUs, cloud infrastructure — where state changes every 50 ms and failure modes are adversarial.

Unlike every other agentic framework, **every Eraya agent has a defined failure path**. When GPU resources are unavailable, latency budgets are exceeded, or upstream models fail, the swarm automatically degrades to a lighter tier and keeps running. The swarm never fully stops.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     OPERATOR CONSOLE                        │
│              Next.js 15 · React 19 · Tailwind v4            │
│         (WebSocket feed · A2A log · Guardian alerts)        │
└────────────────────┬───────────────────────────────────────┘
                     │ WebSocket (Django Channels)
┌────────────────────▼───────────────────────────────────────┐
│                    ERAYA SWARM CORE                         │
│                                                             │
│  ┌──────────────┐  A2A  ┌──────────────┐                   │
│  │  Perceiver   │──────▶│   Planner    │                   │
│  │  (observe)   │◀──────│   (decide)   │                   │
│  └──────┬───────┘       └──────┬───────┘                   │
│         │   ErayaGraph (NX)    │                            │
│  ┌──────▼───────┐       ┌──────▼───────┐                   │
│  │  Recoverer   │◀──────│   Guardian   │                   │
│  │  (heal)      │──────▶│   (secure)   │                   │
│  └──────────────┘  veto └──────────────┘                   │
│                                                             │
│   A2ABus (memory → Redis Streams → NATS JetStream)         │
│   ErayaGraph (NetworkX → Redis pub/sub → Neo4j)            │
└────────────────────┬───────────────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────────────┐
│                  DOMAIN ADAPTERS                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────┐   │
│  │ 5G Telecom │  │   Cloud    │  │   ICU Monitoring   │   │
│  │ (primary)  │  │    Ops     │  │     (stretch)      │   │
│  └────────────┘  └────────────┘  └────────────────────┘   │
└────────────────────────────────────────────────────────────┘
```

---

## The 4 Archetypes

Every archetype is a subclass of `ErayaAgent` and runs the same 3-tier cascade engine automatically.

### 1. PerceiverAgent — Raw signals → structured context

| Tier | Method | Tech |
|------|--------|------|
| Tier 1 (GPU) | Transformer encoder + GNN topology mapper | PyTorch, torch-geometric |
| Tier 2 (CPU) | Kalman filter + XGBoost classifier + HMM refinement | filterpy, xgboost, hmmlearn |
| Tier 3 (always) | Rule-based Bayesian classifier | numpy only |

**Output:** `PerceptionResult` — `state_label`, `confidence`, `risk_score`, `features`, `topology`

```python
perceiver = PerceiverAgent(domain="telecom")
result = perceiver.perceive(raw_signal)
# result.state_label → "handoff_risk" | "congestion" | "normal" | ...
# result.tier_used   → "tier1" | "tier2" | "tier3"
```

### 2. PlannerAgent — Context → optimal actions

| Tier | Method | Tech |
|------|--------|------|
| Tier 1 (GPU) | PPO policy + MCTS lookahead + GNN-conditioned policy | stable-baselines3, PyTorch |
| Tier 2 (CPU) | Thompson Sampling multi-armed bandit + context boost | numpy |
| Tier 3 (always) | Constrained convex optimization | CVXPY (ECOS solver) |

**Key feature:** `BanditArm.update(reward)` is called after every action outcome — the planner learns online without retraining.

```python
planner = PlannerAgent(domain="telecom")
planner.register_actions(env.available_actions())
plan = planner.plan(perception_result)
# plan.requires_guardian_approval → True when risk_score > 0.7
```

### 3. RecovererAgent — Detect degradation, execute fallback

| Tier | Method | Tech |
|------|--------|------|
| Tier 1 (GPU) | Monte Carlo rollout simulator + RL replanning | PyTorch, SB3 |
| Tier 2 (CPU) | Tabular Q-learning + exponential backoff (100ms × 2ⁿ, max 30s) | numpy |
| Tier 3 (always) | Circuit breaker (CLOSED/OPEN/HALF_OPEN) + static fallback policy | pure Python |

```python
recoverer = RecovererAgent(domain="telecom")
recoverer.register_circuit_breaker("sensor_fail", failure_threshold=5)
plan = recoverer.recover(failure_event)
# plan.strategy → "replan" | "backoff" | "circuit_break" | "escalate"
```

### 4. GuardianAgent — Monitor the swarm itself

The security differentiator. Three internal sub-modules:

| Module | Purpose | Tech |
|--------|---------|------|
| `PolicyAuditor` | Hard rules + OPA/Rego evaluation | httpx → OPA REST |
| `InjectionSentinel` | Prompt injection detection | DeBERTa classifier + 13 regex patterns |
| `AuditSigner` | HMAC-SHA256 tamper-evident audit log | hmac, hashlib |

**Hard rules (always enforced, even without OPA):**
- `R001` — ICU actions require perception confidence > 0.8
- `R002` — No action may override a Guardian quarantine
- `R003` — Actions with `risk_score > 0.85` must carry `guardian_approved: true`

**Verdicts:** `APPROVE → WARN → BLOCK → QUARANTINE`

```python
guardian = GuardianAgent(domain="icu", opa_url="http://opa:8181")

# Guard an action
approved, reason = guardian.guard(action, context)

# Scan operator input for injection
is_injection, confidence, reason = guardian.scan_input(user_text)

# Restore a quarantined agent (operator-only)
guardian.lift_quarantine("agent-id", authorized_by="operator-1")
```

---

## The 3-Tier Cascade

Every agent method (`perceive`, `plan`, `recover`) runs through the **same cascade engine** in `ErayaAgent._cascade()`:

```
Signal quality > 0.7 AND GPU available AND latency budget > 100ms
    → Tier 1 (HEAVY)
Signal quality > 0.3 AND latency budget > 30ms
    → Tier 2 (MEDIUM)
Always works
    → Tier 3 (LIGHT)
```

Tier selection is automatic. If a higher tier fails at runtime (import error, OOM, timeout), the engine falls back to the next tier and logs a warning. **The swarm never raises an unhandled exception** — it degrades gracefully.

```python
# Automatic: no agent code calls this directly
def _select_tier(self) -> AgentTier:
    ctx = self._env_ctx
    if ctx.has_gpu and ctx.latency_budget_ms > 100 and ctx.signal_quality > 0.7:
        return AgentTier.HEAVY
    if ctx.latency_budget_ms > 30 and ctx.signal_quality > 0.3:
        return AgentTier.MEDIUM
    return AgentTier.LIGHT
```

---

## A2A Protocol

Inter-agent communication uses **JSON-RPC over WebSocket/NATS** with typed Pydantic schemas.

### Message types

| Type | Direction | Purpose |
|------|-----------|---------|
| `context.update` | Perceiver → Planner | New perception result |
| `action.request` | Planner → Recoverer | Request action execution |
| `action.response` | Recoverer → Planner | Outcome + reward |
| `veto` | Guardian → any | Block an action |
| `quarantine` | Guardian → Bus | Revoke agent's A2A card |
| `capability.query` | any → Bus | Discover agents by capability |
| `capability.response` | Bus → requester | Matching agent cards |
| `heartbeat` | any → Bus | Liveness signal |

### AgentCard — capability discovery

Each agent publishes an `AgentCard` at startup. Other agents query the `A2ABus` to find peers by capability, domain, and trust tier:

```python
bus = get_bus()
planners = bus.find_agents(capability="plan", domain="telecom", trust_tier="high")
```

### Bus backends (automatic fallback)

```
Redis Streams (MVP default)
    → NATS JetStream (production, horizontal scale)
    → in-memory dict (dev / test — always works, no dependencies)
```

---

## ErayaGraph — Shared Context Memory

A thread-safe **NetworkX DiGraph** that all agents in a domain share, with optional Redis pub/sub sync for cross-process consistency.

```python
graph = ErayaGraph.for_domain("telecom")   # singleton per domain

# Add entities
graph.add_node(GraphNode("cell-001", "cell", "telecom", {"rsrp": -80}))
graph.add_edge(GraphEdge("ue-001", "cell-001", "attached_to"))

# Causal path finding
path = graph.causal_path("ue-001", "cell-003")  # used by Planner for MCTS

# Subgraph around a node (for GNN input)
sg = graph.subgraph_around("cell-001", depth=2)
```

**Node types:** `cell`, `patient`, `service`, `agent`, `domain`
**Edge types:** `depends_on`, `monitors`, `affects`, `reports_to`, `attached_to`

---

## Domain Adapters

Adding a new domain requires implementing exactly **3 methods** of `ErayaEnvironment`:

```python
class MyDomain(ErayaEnvironment):
    domain_name = "my_domain"

    def signal_stream(self) -> Iterator[RawSignal]:
        ...  # yield live signals

    def execute_action(self, action: DomainAction) -> ActionOutcome:
        ...  # apply action, return reward

    def reward(self, outcome: ActionOutcome) -> float:
        ...  # scalar reward 0.0–1.0
```

The same 4 agents, the same A2A protocol, and the same Guardian work unchanged.

### 5G Telecom (primary demo)

`FiveGSimulator` generates realistic RAN telemetry for 5 UEs across 3 cells.

| Scenario | Description |
|----------|-------------|
| `NORMAL` | Gaussian noise around baseline |
| `HIGHWAY_HANDOFF` | Oscillating RSRP/SINR at cell boundary |
| `INDOOR_ATTENUATION` | Gradual signal degradation |
| `CONGESTION` | Load-dependent throughput collapse |
| `INTERFERENCE` | SINR drop + packet loss spike |
| `NTN_TRANSITION` | Terrestrial → satellite handover |

**Signals per tick:** `rsrp`, `sinr`, `cqi`, `throughput_mbps`, `latency_ms`, `packet_loss_pct`, `velocity_kmh`

```python
sim = FiveGSimulator(n_ues=5, n_cells=3, tick_ms=500)
sim.inject_scenario(ScenarioType.HIGHWAY_HANDOFF)

for signal in sim.stream():   # infinite
    result = perceiver.perceive(RawSignal(**signal))
```

### Cloud Cost Optimization

Tracks Kubernetes pod metrics, node utilization, and OpenCost spend signals. Actions include pod scaling, node right-sizing, and spot/on-demand rebalancing.

### ICU Monitoring (stretch goal)

MIMIC-IV synthetic patient stream with sepsis early-warning labels. **ICU actions are Guardian-gated by hard rule R001** — all clinical actions require confidence > 0.8 and explicit `guardian_approved: true`.

---

## Real-Time Operator Console

**Frontend:** Next.js 15 + React 19 + Tailwind v4 + react-flow
**State:** Zustand (agents, A2A feed capped at 200 events, incidents, guardian alerts)
**Data:** SWR polling (5s) + auto-reconnecting WebSocket

### Pages

| Route | Purpose |
|-------|---------|
| `/dashboard` | Live swarm overview — agent status, tier distribution, incident count |
| `/agents` | All 4 agents with health metrics and current tier |
| `/agents/[type]` | Deep-dive: per-agent call history, latency, tier breakdown |
| `/domains/[domain]` | Domain signal stream + active scenario |
| `/context-graph` | Interactive react-flow visualization of ErayaGraph |
| `/incidents` | Open/closed incidents with recovery timeline |
| `/audit-log` | Guardian audit log with HMAC verification status |
| `/settings` | Domain selection, latency budget, GPU cap |

### WebSocket channels

```
ws://localhost:8000/ws/eraya/swarm/       ← all events
ws://localhost:8000/ws/eraya/telecom/     ← 5G domain only
ws://localhost:8000/ws/eraya/guardian/    ← vetoes + quarantines only
```

**Event types pushed to frontend:**

| Event | Payload |
|-------|---------|
| `agent.status` | agent_id, role, status, tier, metrics |
| `a2a.message` | from, to, type, domain, payload |
| `guardian.veto` | veto_id, target_agent, reason, severity |
| `incident.created` | incident_id, domain, severity, description |
| `domain.signal` | raw signal dict from simulator |
| `perception.result` | state_label, confidence, risk_score, tier_used |

---

## GPU Configuration

Hardware: **NVIDIA GeForce RTX 4050 Laptop GPU** (6 GB VRAM, CUDA 12.8)

```python
# backend/core/ml/tier1/__init__.py — enforced at import time
torch.cuda.set_per_process_memory_fraction(4.0 / 6.0, device=0)  # ≈ 0.667
```

| Setting | Value |
|---------|-------|
| `GPU_MEMORY_LIMIT_GB` | 4 |
| `RAM_LIMIT_GB` | 8 |
| `ML_DEVICE` | cuda |
| `LATENCY_BUDGET_MS` | 100 |
| PyTorch version | 2.11.0+cu128 |
| stable-baselines3 | 2.8.0 |
| torch-geometric | 2.7.0 |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Django 5.2 · Django REST Framework · Django Channels 4 · Daphne |
| **Async** | Celery + Redis (background tasks) |
| **Frontend** | Next.js 15 · React 19 · Tailwind v4 · react-flow · Zustand · SWR |
| **ML — Tier 1** | PyTorch 2.11+cu128 · stable-baselines3 2.8 · torch-geometric 2.7 |
| **ML — Tier 2** | XGBoost 3.2 · scikit-learn · filterpy (Kalman) · hmmlearn (HMM) |
| **ML — Tier 3** | CVXPY 1.7 (ECOS solver) · NumPy · SciPy |
| **Memory** | NetworkX (in-process graph) · Chroma (vector store) · pgvector |
| **Messaging** | A2A over WebSocket · NATS JetStream · Redis Streams |
| **Security** | OPA + Rego policies · DeBERTa injection detection · HMAC-SHA256 audit |
| **LLM** | Groq (fast inference) · Hugging Face Inference Providers |
| **Observability** | Prometheus · Grafana · structlog |
| **Infra** | Docker Compose · Redis 7 · NATS 2.10 · Chroma |

---

## Quick Start

### Option A — Docker (full stack)

```bash
git clone https://github.com/martian3062/eraya_microsoft.git
cd eraya_microsoft
cp .env.example .env      # fill in your API keys
docker-compose up
```

Open **http://localhost:3000** — operator console
Open **http://localhost:8000/api/** — REST API
Open **http://localhost:9090** — Prometheus (`--profile monitoring`)

### Option B — Local dev (no Docker)

```bash
# 1. Backend
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

pip install -r requirements-dev.txt

# GPU support (CUDA 12.8, optional)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install "stable-baselines3[extra]" torch-geometric

python manage.py migrate
daphne -b 127.0.0.1 -p 8000 eraya.asgi:application

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:3001** (3000 may be occupied on Windows)

---

## Project Structure

```
eraya_microsoft/
├── backend/
│   ├── core/
│   │   ├── agents/
│   │   │   ├── base.py          # ErayaAgent ABC · cascade engine · AgentCard
│   │   │   ├── perceiver.py     # Kalman + XGBoost + HMM → tier cascade
│   │   │   ├── planner.py       # Thompson Sampling + CVXPY → tier cascade
│   │   │   ├── recoverer.py     # Q-learning + circuit breaker → tier cascade
│   │   │   └── guardian.py      # PolicyAuditor + InjectionSentinel + AuditSigner
│   │   ├── a2a/
│   │   │   ├── schemas.py       # Pydantic models: A2AMessage, AgentCard, VetoSignal
│   │   │   └── bus.py           # A2ABus singleton (memory / Redis / NATS)
│   │   ├── memory/
│   │   │   ├── graph.py         # ErayaGraph (NetworkX + Redis sync)
│   │   │   └── vector_store.py  # Chroma vector store wrapper
│   │   └── ml/
│   │       ├── tier1/           # GPU init · VRAM cap enforcement
│   │       ├── tier2/           # CPU ML helpers
│   │       └── tier3/           # CVXPY / rules
│   ├── apps/
│   │   ├── agents/              # AgentInstance model + WebSocket consumer
│   │   ├── audit/               # AuditRecord model (persists GuardianAgent log)
│   │   ├── decisions/           # ActionDecision model (persists ActionPlan history)
│   │   ├── incidents/           # Incident model + REST API
│   │   └── domains/
│   │       ├── base.py          # ErayaEnvironment ABC (3-method contract)
│   │       ├── registry.py      # domain registry
│   │       ├── telecom/         # FiveGSimulator + TelecomEnvironment
│   │       ├── cloud/           # CloudEnvironment + simulator
│   │       └── icu/             # ICUEnvironment + MIMIC-IV simulator
│   ├── eraya/
│   │   ├── settings/            # base / development / production
│   │   ├── asgi.py              # Django Channels ASGI app
│   │   └── urls.py
│   ├── requirements-dev.txt     # minimal (no PyTorch)
│   └── requirements.txt         # full (with PyTorch + SB3)
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/
│   │   │   ├── agents/          # AgentCard · A2AFeed components
│   │   │   ├── graph/           # ContextGraph (react-flow)
│   │   │   └── layout/          # Header · Sidebar
│   │   ├── hooks/
│   │   │   └── use-websocket.ts # auto-reconnecting WS hook
│   │   ├── lib/
│   │   │   └── api.ts           # typed REST client (SWR)
│   │   └── store/
│   │       └── index.ts         # Zustand store
│   └── package.json
├── infrastructure/
│   └── prometheus.yml
├── scripts/
│   ├── setup.sh                 # Linux/macOS setup
│   └── setup.ps1                # Windows setup
├── docker-compose.yml           # backend / frontend / redis / nats / chroma
└── .env.example                 # environment variable template
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in:

```env
# Django
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# ML / GPU
ML_DEVICE=cuda               # or "cpu"
GPU_MEMORY_LIMIT_GB=4
RAM_LIMIT_GB=8
LATENCY_BUDGET_MS=100

# LLM providers
GROQ_API_KEY=gsk_...
HUGGINGFACE_TOKEN=hf_...

# Vector / memory
PINECONE_API_KEY=pcsk_...
CHROMA_HOST=localhost
CHROMA_PORT=8001

# Infrastructure
REDIS_URL=redis://localhost:6379/0
NATS_URL=nats://localhost:4222

# Guardian
ERAYA_AUDIT_KEY=change-me-in-production
OPA_URL=http://localhost:8181   # optional
```

---

## Adding a New Domain

1. Create `backend/apps/domains/mydomain/adapter.py`:

```python
from apps.domains.base import ErayaEnvironment, RawSignal, DomainAction, ActionOutcome
from typing import Iterator

class MyDomainEnvironment(ErayaEnvironment):
    domain_name = "mydomain"

    def signal_stream(self) -> Iterator[RawSignal]:
        while True:
            yield RawSignal(domain="mydomain", source="sensor-1", features={...})

    def execute_action(self, action: DomainAction) -> ActionOutcome:
        return ActionOutcome(action_id=action.action_id, success=True, reward=0.8)

    def reward(self, outcome: ActionOutcome) -> float:
        return outcome.reward
```

2. Register in `backend/apps/domains/registry.py`
3. Add the domain name to `activeDomain` options in `frontend/src/store/index.ts`

The 4 agents, A2A bus, Guardian, and WebSocket stream all work without modification.

---

## Security Model

### Threat model

| Threat | Mitigation |
|--------|-----------|
| Compromised agent takes unauthorized action | Guardian hard rules block before execution |
| Prompt injection via operator console | InjectionSentinel scans all user input |
| Agent impersonation on A2A bus | `AgentCard.trust_tier` + message signatures |
| Audit log tampering | HMAC-SHA256 on every `AuditRecord` |
| Runaway agent flooding the swarm | Automatic quarantine on `QUARANTINE` verdict |
| High-risk actions without oversight | R003: `risk_score > 0.85` requires `guardian_approved` |
| ICU actions on uncertain perception | R001: clinical domain requires confidence > 0.8 |

### GuardianAgent veto flow

```
Agent proposes action
    ↓
Guardian.guard(action, context)
    ├── PolicyAuditor: hard rules R001–R003 (always)
    ├── PolicyAuditor: OPA/Rego (if OPA running)
    └── verdict: APPROVE | WARN | BLOCK | QUARANTINE
         │
    BLOCK     → action rejected, reason returned to caller
    QUARANTINE → agent added to _quarantined_agents
                 all future requests rejected
                 operator must call lift_quarantine() to restore
```

---

## API Reference

### REST endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/agents/` | List all registered agents + health |
| GET | `/api/agents/{id}/` | Single agent detail |
| GET | `/api/incidents/` | List incidents (open by default) |
| POST | `/api/incidents/` | Create incident manually |
| GET | `/api/incidents/{id}/` | Incident detail + recovery timeline |
| GET | `/api/domains/` | List available domains |
| GET | `/api/domains/{name}/snapshot/` | One-shot signal snapshot |
| GET | `/api/audit/` | Guardian audit log (paginated) |
| GET | `/api/decisions/` | Action decision history |

### WebSocket protocol

```json
// Client → Server
{ "type": "ping" }
{ "type": "subscribe", "channel": "guardian" }

// Server → Client
{ "type": "connected",         "channel": "eraya.swarm" }
{ "type": "pong" }
{ "type": "agent.status",      "data": { "agent_id": "...", "status": "active", "tier": "MEDIUM" } }
{ "type": "a2a.message",       "data": { "from": "...", "to": "...", "message_type": "context.update" } }
{ "type": "guardian.veto",     "data": { "veto_id": "...", "severity": "block", "reason": "..." } }
{ "type": "incident.created",  "data": { "incident_id": "...", "domain": "telecom", "severity": "high" } }
{ "type": "perception.result", "data": { "state_label": "handoff_risk", "confidence": 0.87 } }
```

---

## Running Tests

```bash
cd backend
python manage.py test core.agents     # cascade engine unit tests
python manage.py test core.a2a        # A2A bus + schema tests
python manage.py test apps.domains    # domain adapter tests
```

```bash
cd frontend
npm run type-check   # TypeScript compilation
npm run lint         # ESLint
```

---

## Observability

```bash
docker-compose --profile monitoring up
```

| Service | URL | Credentials |
|---------|-----|-------------|
| Prometheus | http://localhost:9090 | — |
| Grafana | http://localhost:3001 | admin / eraya_admin |

Key metrics:
- `eraya_agent_calls_total{role, tier, domain}`
- `eraya_agent_latency_ms{role, tier}`
- `eraya_guardian_vetoes_total{severity, domain}`
- `eraya_cascade_fallbacks_total{from_tier, to_tier}`

---

## Hackathon Differentiators

| Claim | Evidence |
|-------|---------|
| Only framework with defined failure paths | `_cascade()` in `base.py` — tiers 1→2→3, exhausts all options before raising |
| Two hackathon themes in one entry | GuardianAgent = Agent Swarms **+** Security-in-Agentic-Future |
| Live demo with real failure injection | `FiveGSimulator.inject_scenario()` triggers live swarm response on screen |
| GPU-accelerated with hard VRAM cap | `torch.cuda.set_per_process_memory_fraction(0.667)` on RTX 4050 Laptop |
| Pluggable to any domain | `ErayaEnvironment` — 3 methods, zero swarm changes needed |
| Signed tamper-evident audit trail | HMAC-SHA256 on every Guardian decision, verifiable offline |

---

## Team

**Team Eraya** — Microsoft Build AI Hackathon 2026

---

*Built with Django, Next.js, PyTorch, and a lot of respect for failure modes.*
