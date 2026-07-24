from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .registry import get_registered_domains, get_domain


def _get_casper_env():
    return get_domain("casper_defi")


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_list(request):
    domains = get_registered_domains()
    return Response({"domains": [
        {"name": d, "status": "active"} for d in domains
    ]})


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_status(request, domain: str):
    env = get_domain(domain)
    if env is None:
        return Response({"error": f"Domain '{domain}' not registered"}, status=404)
    return Response(env.health_check())


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_signals(request, domain: str):
    env = get_domain(domain)
    if env is None:
        return Response({"error": f"Domain '{domain}' not found"}, status=404)
    signals = []
    for i, sig in enumerate(env.signal_stream()):
        signals.append({
            "timestamp": sig.timestamp,
            "source": sig.source,
            "features": sig.features,
        })
        if i >= 9:
            break
    return Response({"domain": domain, "signals": signals})


@api_view(["GET"])
@permission_classes([AllowAny])
def domain_actions(request, domain: str):
    env = get_domain(domain)
    if env is None:
        return Response({"error": f"Domain '{domain}' not found"}, status=404)
    return Response({"domain": domain, "actions": env.available_actions()})


@api_view(["GET"])
@permission_classes([AllowAny])
def provider_status(request):
    from core.memory import VectorStore
    from core.providers import status

    domain = request.query_params.get("domain", "casper_defi")
    return Response({
        "providers": status(),
        "memory": VectorStore(domain).stats(),
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def rag_ingest(request):
    from core.providers import rag

    domain = request.data.get("domain", "casper_defi")
    url = request.data.get("url", "")
    query = request.data.get("query") or None
    result = rag.ingest_url(domain, url, query)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def rag_query(request):
    from core.providers import rag

    data = request.data if request.method == "POST" else request.query_params
    domain = data.get("domain", "casper_defi")
    query = data.get("q") or data.get("query") or ""
    k = data.get("k", 5)
    result = rag.query(domain, query, k)
    return Response(result, status=200 if result.get("ok") else 400)


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_dashboard(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response(env.dashboard())


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_portfolio(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response(env.portfolio())


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_yields(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response({"yields": env.yield_monitor()})


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_consensus(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response(env.consensus())


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_reputation(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response(env.reputation())


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_transactions(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response({"transactions": env.transactions()})


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_threats(request):
    env = _get_casper_env()
    if env is None:
        return Response({"error": "Casper DeFi domain not registered"}, status=404)
    return Response({"threats": env.threats()})


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_onchain(request):
    """Real on-chain treasury: live account balances from the Casper testnet RPC."""
    from core.casper.onchain import snapshot
    return Response(snapshot())


@api_view(["POST"])
@permission_classes([AllowAny])
def casper_pay(request):
    """Bot autopay — a real Casper testnet transfer (Swarm-ops → Treasury).
    Guardian sets the policy (cap); Recoverer executes. Policy-capped for safety."""
    import os
    from core.casper.onchain import send_transfer, _TREASURY_PK
    try:
        amount = float(request.data.get("amount_cspr", 2.5))
    except (TypeError, ValueError):
        amount = 2.5
    amount = max(2.5, min(amount, 100.0))  # Guardian policy cap
    target = request.data.get("target") or os.environ.get("CASPER_ANCHOR_RECIPIENT", _TREASURY_PK)
    res = send_transfer(target, int(amount * 1_000_000_000)) or {"ok": False, "error": "signing not configured"}
    res["policy"] = {"cap_cspr": 100.0, "route": "Swarm-ops → Treasury",
                     "set_by": "Guardian", "executed_by": "Recoverer"}
    return Response(res, status=200 if res.get("ok") else 400)


@api_view(["POST"])
@permission_classes([AllowAny])
def casper_transcribe(request):
    """Speech-to-text via Groq Whisper — cross-browser voice (no reliance on the
    browser's built-in Google speech service, which throws 'network' on many browsers)."""
    from core.providers import config
    key = config.get("GROQ_API_KEY")
    audio = request.FILES.get("audio")
    if not key:
        return Response({"ok": False, "error": "speech-to-text not configured"}, status=400)
    if not audio:
        return Response({"ok": False, "error": "no audio"}, status=400)
    try:
        import httpx
        files = {"file": (getattr(audio, "name", None) or "audio.webm", audio.read(),
                          getattr(audio, "content_type", None) or "audio/webm")}
        data = {
            "model": "whisper-large-v3-turbo", "response_format": "json", "language": "en",
            "temperature": "0",
            "prompt": "Voice commands for a Casper crypto wallet: send 25 coins, transfer 10 CSPR, "
                      "send 50 coins to treasury, pay 100. Keywords: send, transfer, pay, coins, "
                      "CSPR, tokens, treasury, balance, threats.",
        }
        r = httpx.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {key}"}, data=data, files=files, timeout=45,
        )
        r.raise_for_status()
        return Response({"ok": True, "text": (r.json().get("text") or "").strip()})
    except Exception as exc:
        return Response({"ok": False, "error": str(exc)[:200]}, status=500)


@api_view(["POST"])
@permission_classes([AllowAny])
def casper_speak(request):
    """Text-to-speech via Sarvam (bulbul:v2) — a natural female voice. Returns wav
    audio; the frontend plays it. 502 on failure so the browser voice can fall back."""
    import base64
    from django.http import HttpResponse
    from core.providers import config
    key = config.get("SARVAM_API_KEY")
    text = (request.data.get("text") or "").strip()
    if not key or not text:
        return HttpResponse(status=204)
    lang = request.data.get("lang") or "en-IN"
    speaker = request.data.get("voice") or "anushka"
    try:
        import httpx
        r = httpx.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={"api-subscription-key": key, "Content-Type": "application/json"},
            json={"inputs": [text[:1500]], "target_language_code": lang, "speaker": speaker,
                  "model": "bulbul:v2", "pace": 1.0, "speech_sample_rate": 22050,
                  "enable_preprocessing": True},
            timeout=30,
        )
        r.raise_for_status()
        audios = r.json().get("audios") or []
        if not audios:
            return HttpResponse(status=502)
        return HttpResponse(base64.b64decode(audios[0]), content_type="audio/wav")
    except Exception:
        return HttpResponse(status=502)


@api_view(["POST"])
@permission_classes([AllowAny])
def casper_copilot(request):
    """Advisory Copilot — voice/text Q&A about the swarm + Casper treasury."""
    import json
    q = (request.data.get("question") or "").strip()
    if not q:
        return Response({"answer": "Ask me about the treasury, anomalies, the agent swarm, "
                                   "KAVACHA security, x402, or on-chain anchoring."})
    ctx = {}
    try:
        from core.casper.onchain import snapshot
        s = snapshot()
        ctx["treasury_cspr"] = s.get("total_cspr")
        ctx["network"] = s.get("network")
    except Exception:
        pass
    try:
        env = _get_casper_env()
        if env:
            ctx["active_threats"] = [t.get("type") for t in (env.threats() or [])][:5]
    except Exception:
        pass
    system = (
        "You are ERAYA Copilot, the advisory voice assistant for a live self-healing agentic "
        "DeFi treasury on the Casper blockchain. The swarm has 4 agents (Perceiver, Planner, "
        "Recoverer, Guardian) plus an independent Critic. Capabilities: KAVACHA security "
        "(prompt-injection + A2A spoof defense), statistical network-anomaly intelligence anchored "
        "on Casper testnet, x402 micropayments, TabPFN risk scoring, and bot autopay. Answer like a "
        "concise spoken advisor: 2-3 short sentences, practical and specific. No markdown, no lists "
        "— your reply is read aloud."
    )
    user = f"Live system context: {json.dumps(ctx)}\n\nUser asks: {q}"
    ans = None
    try:
        from core.providers import llm
        out = llm.groq_chat("llama-3.3-70b-versatile", system, user, max_tokens=220, temperature=0.6)
        ans = (out or {}).get("text")
    except Exception:
        ans = None
    if not ans:
        ans = (f"Treasury is {ctx.get('treasury_cspr', '—')} CSPR on {ctx.get('network', 'Casper testnet')}. "
               "I can explain the swarm, anomalies, KAVACHA, x402, or on-chain anchoring — "
               "the language model is momentarily unavailable.")
    return Response({"answer": ans, "context": ctx})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def casper_swarm_chat(request):
    """Live A2A reasoning chat — one coordination round (4 agent messages).
    GET returns the agent roster; POST {trigger, prior} runs a round."""
    from core.casper.swarm_chat import agent_roster, converse
    if request.method == "GET":
        return Response({"agents": agent_roster()})
    trigger = request.data.get("trigger")
    prior = request.data.get("prior") or []
    return Response({"messages": converse(trigger, prior)})


# ─── x402 — agent-economy micropayments (HTTP 402) ────────────────────────────

_MARKET_RESOURCE = "/api/v1/domains/casper_defi/market-data/"


def _market_payload() -> dict:
    from core.casper.mcp import CasperMCPClient
    client = CasperMCPClient()
    pool = client.get_pool_info("cspr-usdc")
    market = client.get_market_snapshot()
    return {
        "cspr_price": 0.0234,
        "volume_24h": int(market.get("tx_volume_24h", 0)),
        "pool_tvl_usd": pool.get("pool_tvl_usd"),
        "apy_current": pool.get("apy_current"),
        "network": client.network,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_market_data(request):
    """Paid resource. Returns 402 + an x402 challenge unless a valid X-Payment
    proof is presented; then returns the market data (x402 flow, steps 1-4)."""
    from core.casper import x402

    if not x402.enabled():
        return Response(_market_payload())

    xpay = request.headers.get("X-Payment", "")
    nonce = request.headers.get("X-Payment-Nonce")
    if xpay:
        result = x402.verify(xpay, _MARKET_RESOURCE, nonce=nonce)
        if result["ok"]:
            payload = _market_payload()
            payload["x402"] = {"paid": True, "verified": result["verified"],
                               "payer": result["payer"], "mode": result["mode"]}
            return Response(payload)
        ch = x402.challenge(_MARKET_RESOURCE)
        resp = Response({**ch, "error": result["reason"]}, status=402)
    else:
        ch = x402.challenge(_MARKET_RESOURCE)
        resp = Response(ch, status=402)
    for k, v in ch["headers"].items():
        resp[k] = v
    return resp


@api_view(["POST"])
@permission_classes([AllowAny])
def x402_verify(request):
    """Facilitator: verify an X-Payment proof (structural + amount + on-chain when
    CSPR.cloud is configured)."""
    from core.casper import x402
    header = request.data.get("x_payment") or request.headers.get("X-Payment", "")
    resource = request.data.get("resource", _MARKET_RESOURCE)
    nonce = request.data.get("nonce")
    return Response(x402.verify(header, resource, nonce=nonce))


# ── Quant Desk: autonomous trading (user sets risk, swarm executes) ──────

@api_view(["GET"])
@permission_classes([AllowAny])
def trading_status(request):
    from core.casper import contracts
    from core.quant import get_engine
    return Response({**get_engine().status(), "contracts": contracts.status()})


@api_view(["POST"])
@permission_classes([AllowAny])
def trading_risk(request):
    from core.quant import get_engine
    try:
        risk = int(request.data.get("risk"))
    except (TypeError, ValueError):
        return Response({"error": "risk must be an integer 1-10"}, status=400)
    return Response({"ok": True, "policy": get_engine().set_risk(risk)})


@api_view(["POST"])
@permission_classes([AllowAny])
def trading_autopilot(request):
    from core.quant import get_engine
    enabled = bool(request.data.get("enabled"))
    return Response({"ok": True, "autopilot": get_engine().set_autopilot(enabled)})


@api_view(["POST"])
@permission_classes([AllowAny])
def trading_tick(request):
    from core.quant import get_engine
    return Response({"ok": True, "tick": get_engine().tick(manual=True)})


@api_view(["POST"])
@permission_classes([AllowAny])
def trading_reset(request):
    from core.quant import get_engine
    get_engine().reset()
    return Response({"ok": True})


_QUANT_RESOURCE = "/api/domains/casper_defi/quant-signal/"
_QUANT_PRICE_MOTES = 5_000_000  # 0.005 CSPR — premium over raw market data


@api_view(["GET"])
@permission_classes([AllowAny])
def casper_quant_signal(request):
    """Paid resource: the swarm's live quant signal, sold to external agents
    over x402. Same 402 -> pay -> retry contract as market-data."""
    from core.casper import x402
    from core.quant import get_engine

    def _payload() -> dict:
        s = get_engine().status()
        sig = s.get("signal", {})
        return {
            "pair": "CSPR/USDT",
            "price": sig.get("price"),
            "score": sig.get("score"),
            "verdict": sig.get("verdict"),
            "threshold": sig.get("threshold"),
            "components": sig.get("components"),
            "rsi14": sig.get("rsi14"),
            "vol_annual_pct": sig.get("vol_annual_pct"),
            "feed": s.get("engine", {}).get("feed"),
            "risk_policy": s.get("risk"),
        }

    if not x402.enabled():
        return Response(_payload())

    xpay = request.headers.get("X-Payment", "")
    nonce = request.headers.get("X-Payment-Nonce")
    if xpay:
        result = x402.verify(xpay, _QUANT_RESOURCE,
                             required_motes=_QUANT_PRICE_MOTES, nonce=nonce)
        if result["ok"]:
            payload = _payload()
            payload["x402"] = {"paid": True, "verified": result["verified"],
                               "payer": result["payer"], "mode": result["mode"]}
            return Response(payload)
        ch = x402.challenge(_QUANT_RESOURCE, amount_motes=_QUANT_PRICE_MOTES)
        resp = Response({**ch, "error": result["reason"]}, status=402)
    else:
        ch = x402.challenge(_QUANT_RESOURCE, amount_motes=_QUANT_PRICE_MOTES)
        resp = Response(ch, status=402)
    for k, v in ch["headers"].items():
        resp[k] = v
    return resp
