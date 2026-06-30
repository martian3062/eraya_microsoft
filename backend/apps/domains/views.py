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
