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
