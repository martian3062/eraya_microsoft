# eraya_microsoft

**ERAYA — Self-Healing Agent Swarm Framework**
*Microsoft Build AI Hackathon 2026 | Theme: Agent Swarms + Security*

> Eraya (एरया) — Sanskrit: "the one that moves toward, navigates, adapts."

---

## What is Eraya?

Eraya is a domain-agnostic **4-archetype agent swarm** that self-heals real-world adaptive systems — 5G networks, hospital ICUs, cloud infrastructure — where state changes every 50ms and failure modes are adversarial.

### The 4 Archetypes

| Agent | Job | Cascade |
|-------|-----|---------|
| 🔍 **Perceiver** | Raw signals → structured context | Transformer+GNN → Kalman+XGBoost+HMM → Bayesian rules |
| 🎯 **Planner** | Context → optimal actions | PPO+MCTS → Thompson Sampling+LSTM → CVXPY |
| 🛟 **Recoverer** | Detect degradation, execute fallback | MC Rollout → Q-learning+backoff → Circuit breaker |
| 🛡️ **Guardian** | Monitor the swarm itself | OPA+DeBERTa → Pattern matching → HMAC audit log |

### Why it wins

- Every agent has a **3-tier graceful degradation cascade** — the only agentic framework where failure paths are defined
- **GuardianAgent** = Security-in-Agentic-Future crossover (two themes in one)
- **Live demo**: inject failures into 5G/Cloud/ICU, watch swarm heal in real-time
- **A2A protocol** for capability discovery and signed task delegation
- **GPU-accelerated** (RTX 4050, 4GB VRAM cap, 8GB RAM cap)

---

## Quick Start

```bash
# Full stack with Docker
docker-compose up

# Manual
cd backend && python -m venv .venv && .venv/Scripts/activate
pip install -r requirements-dev.txt
python manage.py migrate
daphne -b 0.0.0.0 -p 8000 eraya.asgi:application

# Frontend (new terminal)
cd frontend && npm install && npm run dev
```

Open: http://localhost:3000 (operator console)

---

## Stack

**Backend**: Django 5.2 + Channels + DRF + Celery  
**Frontend**: Next.js 15 + React 19 + Tailwind v4 + react-flow  
**ML**: PyTorch (CUDA 12.8) + XGBoost + Kalman + HMM + CVXPY  
**Memory**: NetworkX + Chroma + pgvector  
**Protocol**: A2A (JSON-RPC over WebSocket/NATS) + MCP  
**Security**: OPA + Rego + NeMo Guardrails + HMAC audit log  
**LLM**: Groq (fast) + Hugging Face Inference Providers  

## Demo Domains

1. **5G Self-Healing** (primary) — Open5GS + UERANSIM + Python simulator
2. **Cloud Cost Optimization** — Kubernetes + OpenCost + Prometheus  
3. **ICU Monitoring** (stretch) — MIMIC-IV synthetic stream + sepsis early warning

---

*Built by Team Eraya for Microsoft Build AI Hackathon 2026*
