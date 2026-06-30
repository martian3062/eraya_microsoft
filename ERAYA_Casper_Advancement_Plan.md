# ERAYA → Casper: Advancement Plan

## What ERAYA Currently Has vs. What's Missing

### ✅ Already Strong (Keep As-Is)
- 4-archetype swarm (Perceiver, Planner, Recoverer, Guardian)
- 3-tier cascade engine with automatic fallback
- KAVACHA security (DeBERTa injection, R001-R003, HMAC audit)
- A2A protocol with HMAC-signed messages
- ErayaGraph context memory (NetworkX)
- MCP server (8 tools)
- OpenTelemetry distributed traces
- LLM Planner (Groq llama-3.3-70b)
- Next.js operator console with attack demo
- Domain-agnostic 3-method adapter contract

### ❌ Current Gaps (What Judges Will Notice)

| Gap | Why It Hurts | Casper Fix |
|-----|-------------|------------|
| **Agents don't interact with any blockchain** | "Agentic Buildathon" requires on-chain tx | Casper testnet deployment via CSPR.click Agent Skill |
| **No agent economy** | Agents communicate free; no economic skin-in-the-game | x402 micropayments — agents pay per API request |
| **No on-chain identity** | AgentCards are in-memory only, not verifiable | On-chain Agent Registry contract (Odra) |
| **No multi-agent consensus** | PlannerAgent decides alone on critical actions | Swarm Quorum Protocol — agents vote before high-stakes execution |
| **No real external data feeds** | All 3 domains use simulators | CSPR.cloud APIs + CSPR.trade MCP for real DeFi data |
| **Tier 1 GPU is mostly stubs** | PPO/MCTS/GNN placeholders, not trained | Replace with fine-tuned LLM chain (Groq multi-step reasoning) |
| **KAVACHA is reactive only** | Detects attacks post-submission, doesn't hunt | Add proactive Threat Scanner that monitors mempool/proposals |
| **No autonomous contract execution** | Agents propose actions but a human runs them | Agents sign and submit Casper transactions autonomously |
| **No agent reputation tracking** | No performance history, no trust scoring | On-chain reputation ledger — accuracy over time |
| **No agent spawning/scaling** | Fixed 4 agents, can't scale to load | Dynamic agent pool with Celery workers |
| **ErayaGraph resets on restart** | No persistence across sessions | Redis + on-chain state snapshots |

---

## PRIORITY 1: Casper Integration Layer (Must-Have, ~2 days)

### 1A. DeFi Domain Adapter — `CasperDeFiEnvironment`

New domain adapter following the existing 3-method contract:

```python
# apps/domains/casper_defi/environment.py
class CasperDeFiEnvironment(ErayaEnvironment):
    domain_name = "casper_defi"

    def signal_stream(self) -> Iterator[RawSignal]:
        """
        Pulls real data from CSPR.cloud APIs + CSPR.trade MCP:
        - DEX pool reserves, TVL, APY across Casper DeFi protocols
        - Gas prices, transaction volume, mempool depth
        - Token prices, liquidity depth, slippage estimates
        - Governance proposal status, voting power distribution
        """

    def execute_action(self, action: DomainAction) -> ActionOutcome:
        """
        Actions via CSPR.click Agent Skill:
        - swap(token_a, token_b, amount) — execute DEX swap
        - stake(validator, amount) — delegate CSPR
        - vote(proposal_id, direction) — cast DAO vote
        - rebalance(portfolio, target_weights) — multi-step reallocation
        - deploy_contract(wasm_path, args) — deploy via Odra
        """

    def reward(self, outcome: ActionOutcome) -> float:
        """
        DeFi-specific reward signals:
        - Yield delta (APY improvement after rebalance)
        - Slippage cost (penalty for bad execution)
        - Gas efficiency (lower = better)
        - Proposal outcome alignment (did the vote win?)
        """
```

**Features for PerceiverAgent:**
```
casper_defi signal features:
├── pool_tvl_usd          # Total value locked in target pool
├── apy_current            # Current annual percentage yield
├── apy_7d_avg             # 7-day moving average APY
├── gas_price_motes        # Current gas price in motes
├── tx_volume_24h          # 24-hour transaction volume
├── slippage_estimate_bps  # Expected slippage in basis points
├── liquidity_depth_usd    # Orderbook/pool depth
├── governance_quorum_pct  # Current quorum reached on active proposals
├── validator_uptime_pct   # Target validator performance
└── mempool_pending_count  # Pending transactions (congestion signal)
```

### 1B. Casper MCP Integration — Rewire MCP Server

Replace custom REST-based MCP with Casper's native MCP servers:

```python
# mcp_integration/casper_mcp.py

CASPER_MCP_SERVERS = {
    "casper_chain": {
        "url": "https://casper-mcp-server-url",  # Casper MCP Server
        "tools": [
            "query_balance",
            "get_deploy_info",
            "get_block",
            "query_contract_state",
            "get_validator_info",
        ]
    },
    "cspr_trade": {
        "url": "https://cspr-trade-mcp-url",  # CSPR.trade MCP
        "tools": [
            "get_token_price",
            "execute_swap",
            "get_pool_info",
            "get_portfolio",
            "place_limit_order",
        ]
    }
}
```

**PerceiverAgent now has two data sources:**
- Tier 1: CSPR.cloud Streaming API (real-time WebSocket feed)
- Tier 2: CSPR.cloud REST API (polling every 5s)
- Tier 3: Cached last-known state (always available)

### 1C. CSPR.click Agent Skill — Transaction Signing

Every agent gets a Casper wallet via CSPR.click:

```python
# core/casper/wallet.py
class AgentWallet:
    """Each ERAYA agent gets a Casper testnet wallet"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        # CSPR.click creates wallet, stores keys securely
        self.account_hash = cspr_click.create_wallet(agent_id)

    async def sign_and_submit(self, deploy: Deploy) -> DeployHash:
        """Sign a Casper deploy and submit to testnet"""
        signed = cspr_click.sign(deploy, self.agent_id)
        return await cspr_cloud.submit_deploy(signed)

    async def get_balance(self) -> int:
        """Query CSPR balance in motes"""
        return await casper_mcp.query_balance(self.account_hash)
```

### 1D. Odra Smart Contracts — Deploy on Casper Testnet

Three contracts that give ERAYA on-chain presence:

```
contracts/
├── agent_registry/          # On-chain agent identity + capabilities
│   └── src/lib.rs           # register_agent, update_status, get_card
├── treasury/                # DeFi treasury managed by swarm
│   └── src/lib.rs           # deposit, withdraw, rebalance, get_holdings
├── governance/              # DAO proposal + voting
│   └── src/lib.rs           # create_proposal, cast_vote, execute, quorum_check
└── reputation/              # Agent performance ledger
    └── src/lib.rs           # record_outcome, get_score, slash, reward
```

**Agent Registry Contract (Odra):**
```rust
#[odra::module]
pub struct AgentRegistry {
    agents: Mapping<AccountHash, AgentCard>,
    active_count: Var<u32>,
}

#[odra::module]
impl AgentRegistry {
    pub fn register_agent(&mut self, role: String, domain: String,
                          capabilities: Vec<String>, trust_tier: String) {
        let card = AgentCard {
            agent_id: self.env().caller(),
            role, domain, capabilities, trust_tier,
            registered_at: self.env().get_block_time(),
            reputation_score: 1000, // starts at 1000
            status: "active".into(),
        };
        self.agents.set(&self.env().caller(), card);
        self.active_count.set(self.active_count.get_or_default() + 1);
    }

    pub fn update_status(&mut self, agent: AccountHash, status: String) {
        // Only Guardian can quarantine other agents
        let mut card = self.agents.get(&agent).unwrap();
        card.status = status;
        self.agents.set(&agent, card);
    }

    pub fn get_card(&self, agent: AccountHash) -> AgentCard {
        self.agents.get(&agent).unwrap()
    }
}
```

---

## PRIORITY 2: Agent Economy Layer (High Impact, ~1 day)

### 2A. x402 Micropayments Between Agents

The current A2ABus is free — agents communicate without cost. Adding x402 creates an **economic layer** where agents pay for services:

```python
# core/a2a/x402_bus.py
class X402EnabledBus(A2ABus):
    """A2A bus where inter-agent API calls cost micropayments via x402"""

    async def publish(self, message: A2AMessage) -> bool:
        # High-value requests (planning, recovery) cost more
        cost = self._price_message(message)

        if cost > 0:
            # Agent pays via x402 protocol on Casper
            payment_proof = await x402.pay(
                from_agent=message.from_agent,
                to_agent=message.to_agent,
                amount_motes=cost,
                purpose=message.message_type
            )
            message.payment_proof = payment_proof

        return await super().publish(message)

    def _price_message(self, msg: A2AMessage) -> int:
        """Price schedule for inter-agent services"""
        prices = {
            "context.update": 0,          # Free — common good
            "capability.query": 0,        # Free — discovery
            "heartbeat": 0,               # Free — health
            "action.request": 100_000,    # 0.1 CSPR — planning is valuable
            "action.response": 0,         # Free — response to paid request
            "veto": 50_000,               # 0.05 CSPR — Guardian work
        }
        return prices.get(msg.message_type, 10_000)
```

**Why this matters:** Casper's x402 is their flagship AI feature. Using it in A2ABus is a direct integration that judges will notice immediately. It also creates a natural incentive mechanism — agents that provide bad plans lose CSPR, agents that are accurate earn more.

### 2B. Agent Reputation System (On-Chain)

```python
# core/reputation/tracker.py
class ReputationTracker:
    """Tracks agent performance and records on-chain via reputation contract"""

    async def record_outcome(self, agent_id: str, action_id: str,
                              success: bool, reward: float):
        # Update local EMA
        self.ema_scores[agent_id] = 0.9 * self.ema_scores[agent_id] + 0.1 * reward

        # Record on-chain every N outcomes (batched for gas efficiency)
        self.pending_records.append(ReputationRecord(
            agent_id=agent_id, action_id=action_id,
            success=success, reward=reward,
            timestamp=int(time.time())
        ))

        if len(self.pending_records) >= 10:
            await self._flush_to_chain()

    async def get_trust_score(self, agent_id: str) -> float:
        """Query on-chain reputation score"""
        return await reputation_contract.get_score(agent_id)

    async def slash(self, agent_id: str, reason: str, amount: int):
        """Guardian slashes bad actors"""
        await reputation_contract.slash(agent_id, amount, reason)
```

---

## PRIORITY 3: Multi-Agent Consensus Protocol (Differentiator, ~1 day)

### 3A. Swarm Quorum — Agents Vote Before High-Stakes Execution

Currently PlannerAgent decides alone. For DeFi, high-stakes decisions need swarm consensus:

```python
# core/consensus/quorum.py
class SwarmQuorum:
    """
    Multi-agent voting protocol for high-stakes decisions.
    Maps to Casper DAO governance example build #3.
    """

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold  # 60% majority required
        self.active_proposals: dict[str, Proposal] = {}

    async def propose(self, proposer: str, action: ActionPlan,
                      context: PerceptionResult) -> Proposal:
        proposal = Proposal(
            id=uuid4(), proposer=proposer,
            action=action, context=context,
            votes={}, status="voting",
            created_at=time.time(), deadline=time.time() + 30  # 30s voting window
        )
        self.active_proposals[proposal.id] = proposal

        # Broadcast to all agents via A2A
        await a2a_bus.broadcast(A2AMessage(
            message_type="consensus.propose",
            payload=proposal.to_dict()
        ))
        return proposal

    async def cast_vote(self, proposal_id: str, agent_id: str,
                        vote: Literal["approve", "reject", "abstain"],
                        rationale: str):
        proposal = self.active_proposals[proposal_id]
        proposal.votes[agent_id] = Vote(vote=vote, rationale=rationale)

        # Check if quorum reached
        if self._quorum_reached(proposal):
            if self._majority_approves(proposal):
                proposal.status = "approved"
                # Execute on-chain via governance contract
                await governance_contract.execute(proposal.action)
                # Record on-chain vote for transparency
                await governance_contract.record_vote(proposal)
            else:
                proposal.status = "rejected"

    def _quorum_reached(self, p: Proposal) -> bool:
        return len(p.votes) >= 3  # At least 3 of 4 agents voted

    def _majority_approves(self, p: Proposal) -> bool:
        approvals = sum(1 for v in p.votes.values() if v.vote == "approve")
        return approvals / len(p.votes) >= self.threshold
```

### 3B. When Does Quorum Trigger?

Not every action needs a vote. Only high-stakes DeFi decisions:

```python
# In PlannerAgent.plan():
if action.risk_score > 0.7 or action.value_usd > 10000:
    # High-stakes → require swarm consensus
    proposal = await quorum.propose(self.agent_id, action, context)
    # Wait for vote resolution (max 30s)
    result = await proposal.wait_for_resolution()
    if result.status != "approved":
        return ActionPlan(action="hold", rationale=f"Swarm rejected: {result.rejection_reasons}")
else:
    # Low-stakes → PlannerAgent decides alone (existing flow)
    pass
```

### 3C. What Each Agent Votes On

| Agent | Voting Logic | Example |
|-------|-------------|---------|
| **PerceiverAgent** | "Is the data supporting this decision reliable?" | Votes NO if signal confidence < 0.6 |
| **PlannerAgent** | "Is the expected reward worth the risk?" | Votes YES if Sharpe ratio > 1.5 |
| **RecovererAgent** | "Can we recover if this goes wrong?" | Votes NO if circuit breaker is OPEN |
| **GuardianAgent** | "Does this pass all policy rules?" | Votes NO if R003–R006 fire |

---

## PRIORITY 4: New KAVACHA DeFi Security Rules (~0.5 day)

### 4A. DeFi-Specific Policy Rules

Extend PolicyAuditor with DeFi rules:

```python
# R004–R008: DeFi-specific hard rules
DEFI_RULES = {
    "R004": {
        "name": "Treasury Concentration Limit",
        "condition": "single_position_pct > 0.25",
        "action": "BLOCK",
        "description": "No single position can exceed 25% of treasury TVL"
    },
    "R005": {
        "name": "Swap Size Gate",
        "condition": "swap_value_usd > treasury_tvl * 0.05",
        "action": "BLOCK",
        "description": "Single swap cannot exceed 5% of treasury"
    },
    "R006": {
        "name": "Yield Chasing Guard",
        "condition": "target_apy > 3 * market_avg_apy",
        "action": "WARN",
        "description": "APY >3x market average likely unsustainable/scam"
    },
    "R007": {
        "name": "Slippage Protection",
        "condition": "estimated_slippage_bps > 100",
        "action": "BLOCK",
        "description": "Block swaps with >1% estimated slippage"
    },
    "R008": {
        "name": "Rug Pull Detection",
        "condition": "liquidity_drop_24h_pct > 0.50",
        "action": "QUARANTINE",
        "description": "Quarantine pool interaction if liquidity dropped >50% in 24h"
    }
}
```

### 4B. Proactive Threat Scanner (New KAVACHA Capability)

Current KAVACHA is reactive. Add proactive monitoring:

```python
# core/agents/threat_scanner.py
class ThreatScanner:
    """
    Proactive security — monitors Casper mempool and DeFi state
    for threats BEFORE they hit the swarm.
    """

    async def scan_cycle(self):
        threats = []

        # 1. Mempool analysis — detect front-running attempts
        pending = await cspr_cloud.get_pending_deploys()
        for deploy in pending:
            if self._is_sandwich_attack(deploy, self.known_positions):
                threats.append(Threat("sandwich_attack", deploy, severity=0.9))

        # 2. Liquidity monitoring — detect rug pull signals
        for pool in self.watched_pools:
            state = await casper_mcp.query_contract_state(pool.address)
            if state.liquidity < pool.last_liquidity * 0.7:
                threats.append(Threat("liquidity_drain", pool, severity=0.8))

        # 3. Governance attack detection — flash loan voting
        proposals = await governance_contract.get_active_proposals()
        for prop in proposals:
            if self._suspicious_voting_pattern(prop):
                threats.append(Threat("governance_attack", prop, severity=0.85))

        # 4. Broadcast threats to Guardian
        for threat in threats:
            await a2a_bus.publish(A2AMessage(
                from_agent="threat_scanner",
                to_agent="guardian",
                message_type="threat.detected",
                payload=threat.to_dict()
            ))
```

---

## PRIORITY 5: Enhanced Frontend — DeFi Dashboard (~0.5 day)

### New Pages for Casper DeFi

```
New routes:
├── /defi/portfolio          # Treasury holdings, allocation pie chart, P&L
├── /defi/yield-monitor      # Live APY tracking across Casper protocols
├── /defi/swarm-consensus    # Active proposals, voting status, agent rationales
├── /defi/reputation         # Agent trust scores, performance history
├── /defi/transactions       # On-chain transaction log with Casper explorer links
└── /defi/threat-radar       # ThreatScanner live feed, mempool visualization
```

### Swarm Consensus UI (New, High-Impact for Demo)

```
┌─────────────────────────────────────────────────┐
│  SWARM CONSENSUS: Proposal #47                   │
│  "Rebalance treasury: 30% CSPR → 20% CSPR + 10% USDT"  │
│                                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  │ PERCEIVER│  │ PLANNER  │  │ RECOVERER│  │ GUARDIAN  │
│  │   ✅ YES │  │   ✅ YES │  │   ⏳ ...  │  │   ❌ NO  │
│  │ "data    │  │ "Sharpe  │  │ voting..  │  │ "R005:   │
│  │  solid"  │  │  = 1.8"  │  │           │  │  >5%"    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘
│                                                   │
│  Quorum: 3/4 voted | Threshold: 60% | Status: ⏳   │
│  [View on Casper Explorer →]                       │
└─────────────────────────────────────────────────┘
```

---

## PRIORITY 6: Architecture Upgrades (Nice-to-Have)

### 6A. Agent Spawning Pool

```python
# core/pool/spawner.py
class AgentPool:
    """Dynamically spawn/despawn agents based on load"""

    def scale_up(self, role: str, domain: str, count: int = 1):
        for _ in range(count):
            agent = self.agent_factory.create(role, domain)
            # Register on-chain
            await agent_registry.register_agent(agent.card)
            # Start as Celery worker
            self.workers.append(agent.start_as_worker())

    def scale_down(self, role: str, count: int = 1):
        # Graceful shutdown — finish current task, deregister on-chain
        pass

    def auto_scale(self):
        """Scale based on signal volume and risk level"""
        if self.metrics.avg_latency_ms > 200:
            self.scale_up("perceiver", self.domain)
        if self.metrics.pending_plans > 10:
            self.scale_up("planner", self.domain)
```

### 6B. Cross-Agent Knowledge Sharing

```python
# core/learning/shared_memory.py
class SharedLearningMemory:
    """
    Agents share learned insights via ErayaGraph + vector store.
    Thompson Sampling arms are shared across Planner instances.
    """

    async def share_insight(self, agent_id: str, insight: Insight):
        # Store in vector DB for semantic retrieval
        await vector_store.upsert(
            id=insight.id,
            embedding=embed(insight.description),
            metadata={"agent": agent_id, "domain": insight.domain,
                      "reward": insight.reward, "timestamp": insight.timestamp}
        )
        # Update ErayaGraph — add knowledge edge
        graph.add_edge(GraphEdge(
            agent_id, f"insight-{insight.id}",
            edge_type="learned", weight=insight.confidence
        ))

    async def query_relevant(self, context: str, top_k: int = 5) -> list[Insight]:
        return await vector_store.query(embed(context), top_k=top_k)
```

### 6C. Replace Tier 1 GPU Stubs with Multi-Step LLM Reasoning

Instead of untrained PPO/MCTS (stubs), make Tier 1 a multi-step LLM chain:

```python
# core/agents/llm_planner.py — enhanced
class EnhancedLLMPlanner(LLMPlannerAgent):
    """Tier 1: Multi-step reasoning chain instead of PPO stub"""

    async def _plan_tier1(self, perception: PerceptionResult) -> ActionPlan:
        # Step 1: Situation analysis
        analysis = await self.llm.analyze(
            f"DeFi state: {perception.features}\n"
            f"Risk score: {perception.risk_score}\n"
            f"Analyze the current situation and identify opportunities/threats."
        )

        # Step 2: Strategy generation (multiple candidates)
        strategies = await self.llm.generate_strategies(
            analysis, self.available_actions, n=3
        )

        # Step 3: Risk assessment per strategy
        assessed = []
        for strategy in strategies:
            risk = await self.llm.assess_risk(strategy, perception)
            assessed.append((strategy, risk))

        # Step 4: Select optimal strategy
        best = min(assessed, key=lambda x: x[1].expected_loss)

        # Step 5: Generate execution plan
        return await self.llm.create_execution_plan(
            best[0], perception,
            format="ActionPlan JSON"
        )
```

---

## Implementation Order (7 Days to July 7)

| Day | Priority | Task | Hours |
|-----|----------|------|-------|
| Day 1 (Jul 1) | P1 | CasperDeFiEnvironment adapter + CSPR.cloud API integration | 6h |
| Day 1 (Jul 1) | P1 | CSPR.click wallet setup for all 4 agents | 2h |
| Day 2 (Jul 2) | P1 | Casper MCP Server + CSPR.trade MCP integration in PerceiverAgent | 5h |
| Day 2 (Jul 2) | P1 | Odra contracts: AgentRegistry + Treasury (scaffold + deploy testnet) | 3h |
| Day 3 (Jul 3) | P2 | x402 micropayments in A2ABus | 4h |
| Day 3 (Jul 3) | P2 | Reputation tracker + on-chain recording | 3h |
| Day 4 (Jul 4) | P3 | SwarmQuorum consensus protocol | 5h |
| Day 4 (Jul 4) | P3 | Governance contract (Odra) + vote recording | 3h |
| Day 5 (Jul 5) | P4 | DeFi KAVACHA rules R004–R008 | 3h |
| Day 5 (Jul 5) | P4 | Proactive ThreatScanner (mempool + liquidity monitoring) | 3h |
| Day 5 (Jul 5) | P5 | DeFi dashboard pages (portfolio, consensus, reputation) | 2h |
| Day 6 (Jul 6) | P5 | Consensus UI + transaction log with Casper explorer links | 4h |
| Day 6 (Jul 6) | — | Integration testing, testnet deployment verification | 3h |
| Day 7 (Jul 7) | — | README update, demo video recording, submission | 4h |

**Total: ~50 hours across 7 days**

---

## Updated Architecture Diagram (After All Additions)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        OPERATOR CONSOLE (Next.js 15)                     │
│   Dashboard · DeFi Portfolio · Swarm Consensus · Reputation ·            │
│   Threat Radar · KAVACHA Attack Console · Transaction Log               │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │ WebSocket (Django Channels 4)
┌──────────────────────────▼──────────────────────────────────────────────┐
│                       ERAYA SWARM CORE                                   │
│                                                                          │
│  ┌─────────────────┐  A2A (HMAC + x402 💰)  ┌──────────────────────┐  │
│  │  PerceiverAgent │────────────────────────▶│  PlannerAgent         │  │
│  │  Casper MCP     │◀────────────────────────│  Multi-step LLM      │  │
│  │  CSPR.cloud API │                         │  Thompson Sampling    │  │
│  └────────┬────────┘                         └────────┬─────────────┘  │
│           │          SwarmQuorum 🗳️                    │                │
│           │    ┌──────────────────────┐                │                │
│           ├───▶│  Consensus Protocol  │◀───────────────┤                │
│           │    │  Vote → Execute      │                │                │
│           │    └──────────┬───────────┘                │                │
│  ┌────────▼────────┐     │     ┌──────────────────────▼──────────────┐ │
│  │  RecovererAgent │     │     │      KAVACHA (Guardian)              │ │
│  │  Circuit Breaker│     │     │  InjectionSentinel (DeBERTa)        │ │
│  │  Casper tx retry│     │     │  PolicyAuditor R001–R008            │ │
│  └─────────────────┘     │     │  AuditSigner (HMAC-256)            │ │
│                          │     │  ThreatScanner 🔍 (NEW)            │ │
│                          │     │  Reputation Tracker 📊 (NEW)       │ │
│                          │     └──────────────────────────────────────┘ │
│                          │                                              │
│  A2ABus: x402 micropayments · Redis Streams · NATS JetStream          │
│  ErayaGraph: NetworkX → Redis · On-chain state snapshots               │
│  AgentWallet: CSPR.click per agent · Casper testnet                    │
│  OTel spans → Jaeger                                                    │
└──────────────────────────┬──────────────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────────────┐
│                    CASPER BLOCKCHAIN LAYER                                │
│                                                                          │
│  ┌────────────────┐  ┌──────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ AgentRegistry  │  │ Treasury │  │ Governance │  │  Reputation   │  │
│  │ (Odra)         │  │ (Odra)   │  │ (Odra)     │  │  (Odra)       │  │
│  │ On-chain       │  │ DeFi     │  │ Proposals  │  │  Trust scores │  │
│  │ agent cards    │  │ holdings │  │ + voting   │  │  + slashing   │  │
│  └────────────────┘  └──────────┘  └────────────┘  └───────────────┘  │
│                                                                          │
│  Casper MCP Server · CSPR.trade MCP · CSPR.click · x402 · CSPR.cloud  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## What Makes This Win — Differentiators vs. Other Submissions

| What others will build | What ERAYA brings that they won't |
|---|---|
| Single AI agent calling a DEX | **4 specialized agents** with defined failure paths for each |
| Agent that just executes trades | Agents that **vote on decisions**, then execute with Guardian approval |
| No security layer | **KAVACHA** — injection detection, policy audit, HMAC-signed audit log |
| Agents with no economic incentive | **x402 micropayments** — agents pay each other for services |
| No observability | **Full OTel traces** — see every cascade tier, every A2A message |
| No failure handling | **3-tier cascade** — GPU → CPU → rules, never fully stops |
| No on-chain identity | **Agent Registry** — verifiable agent cards on Casper |
| Reactive security only | **ThreatScanner** — proactive mempool + liquidity monitoring |
| Solo agent decisions | **SwarmQuorum** — multi-agent consensus for high-stakes DeFi |
| No reputation tracking | **On-chain reputation** — slash bad agents, reward good ones |
| "Demo" that's a Jupyter notebook | **Full Next.js console** with live DeFi dashboard + attack demo |

---

## Hackathon Judging Criteria → ERAYA Feature Map

| Criterion | ERAYA Feature | Score Prediction |
|---|---|---|
| Technical Execution | 3-tier cascade, OTel traces, Odra contracts, full test suite | 9/10 |
| Innovation & Originality | Self-healing immune-system model for DeFi agents — nobody else has this | 9/10 |
| Use of AI / Agentic Systems | 4 autonomous agents + LLM + online learning + multi-agent consensus | 10/10 |
| Real-World Applicability | Autonomous DeFi treasury management on Casper | 8/10 |
| User Experience & Design | Full Next.js dashboard + consensus UI + attack console | 8/10 |
| Working Smart Contracts | 4 Odra contracts on Casper Testnet with real transactions | 9/10 |
| Long-Term Launch Plans | Patent filed, 5 IEEE pubs, active GitHub, portfolio site | 9/10 |
| Ecosystem Impact | First multi-agent security framework on Casper + uses ALL Casper AI toolkit components | 10/10 |
