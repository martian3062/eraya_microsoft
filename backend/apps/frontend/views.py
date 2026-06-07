import json
import os
import secrets
import urllib.parse

import httpx
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

MAJOR_NAV = [
    {"id": "dashboard", "label": "Home",     "icon": "layout-dashboard", "href": "/dashboard/"},
    {"id": "agents",    "label": "Agents",   "icon": "bot",              "href": "/agents/perceiver/"},
    {"id": "domains",   "label": "Domains",  "icon": "activity",         "href": "/domains/5g/"},
    {"id": "security",  "label": "Security", "icon": "shield",           "href": "/security/"},
]
FLAT_NAV = [
    {"id": "map",           "label": "Global Map",    "icon": "map",            "href": "/map/"},
    {"id": "a2a-chat",      "label": "A2A Chat",      "icon": "radio",          "href": "/a2a-chat/"},
    {"id": "self-healing",  "label": "Self-Heal",     "icon": "heart-pulse",    "href": "/self-healing/"},
    {"id": "context-graph", "label": "Context Graph", "icon": "git-branch",     "href": "/context-graph/"},
    {"id": "incidents",     "label": "Incidents",     "icon": "alert-triangle", "href": "/incidents/"},
    {"id": "audit-log",     "label": "Audit Log",     "icon": "file-text",      "href": "/audit-log/"},
    {"id": "settings",      "label": "Settings",      "icon": "settings",       "href": "/settings/"},
]


def _ctx(request, page, **extra):
    name = (
        request.session.get("user_name")
        or (request.user.first_name or request.user.email
            if request.user.is_authenticated else "Guest")
    )
    return {
        "page":        page,
        "major_nav":   MAJOR_NAV,
        "flat_nav":    FLAT_NAV,
        "user_name":   name,
        "user_picture":request.session.get("user_picture", ""),
        "user_role":   request.session.get("user_role", "operator"),
        **extra,
    }


def _is_authed(request):
    return request.user.is_authenticated or bool(request.session.get("user_role"))


def _require_auth(fn):
    def wrapper(request, *args, **kwargs):
        if not _is_authed(request):
            return redirect("login")
        return fn(request, *args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# ── Auth views ────────────────────────────────────────────────────────────────

def login_view(request):
    if _is_authed(request):
        return redirect("dashboard")
    error = request.GET.get("error", "")
    return render(request, "frontend/login.html", {"error": error})


@csrf_exempt
@require_http_methods(["POST"])
def credential_login(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    user = authenticate(request, username=email, password=password)
    if user:
        login(request, user)
        request.session["user_name"] = user.first_name or user.email or email
        request.session["user_role"] = "operator"
        return JsonResponse({"ok": True})
    return JsonResponse({"error": "Invalid email or password"}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def credential_register(request):
    try:
        data = json.loads(request.body)
    except Exception:
        data = request.POST.dict()
    email    = (data.get("email") or "").strip().lower()
    password = data.get("password", "")
    name     = (data.get("name") or "").strip() or email.split("@")[0]
    if not email or not password:
        return JsonResponse({"error": "Email and password required"}, status=400)
    if len(password) < 6:
        return JsonResponse({"error": "Password must be at least 6 characters"}, status=400)
    if User.objects.filter(username=email).exists():
        return JsonResponse({"error": "Account already exists"}, status=409)
    user = User.objects.create_user(username=email, email=email, password=password, first_name=name)
    login(request, user)
    request.session["user_name"] = name
    request.session["user_role"] = "operator"
    return JsonResponse({"ok": True})


def guest_login(request):
    request.session["user_name"] = "Guest"
    request.session["user_role"] = "guest"
    return redirect("dashboard")


@csrf_exempt
def operator_login(request):
    name = (request.POST.get("name") or request.GET.get("name") or "Operator").strip()
    request.session["user_name"] = name
    request.session["user_role"] = "operator"
    return redirect("dashboard")


def google_auth_start(request):
    if not GOOGLE_CLIENT_ID:
        return redirect("/?error=google_not_configured")
    state = secrets.token_urlsafe(16)
    request.session["oauth_state"] = state
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  request.build_absolute_uri("/auth/google/callback/"),
        "scope":         "openid email profile",
        "response_type": "code",
        "state":         state,
        "access_type":   "online",
    }
    return redirect("https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params))


def google_auth_callback(request):
    code  = request.GET.get("code", "")
    state = request.GET.get("state", "")
    if state != request.session.get("oauth_state", "NONE"):
        return redirect("/?error=oauth_state")
    redirect_uri = request.build_absolute_uri("/auth/google/callback/")
    try:
        with httpx.Client(timeout=10) as client:
            tokens = client.post("https://oauth2.googleapis.com/token", data={
                "code": code, "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri, "grant_type": "authorization_code",
            }).json()
            info = client.get("https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {tokens.get('access_token','')}"},
            ).json()
    except Exception:
        return redirect("/?error=google_failed")
    email   = info.get("email", "")
    name    = info.get("name", email)
    picture = info.get("picture", "")
    if not email:
        return redirect("/?error=no_email")
    user, _ = User.objects.get_or_create(username=email, defaults={"email": email, "first_name": name})
    if not user.first_name:
        user.first_name = name; user.save(update_fields=["first_name"])
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["user_name"]    = name
    request.session["user_picture"] = picture
    request.session["user_role"]    = "operator"
    return redirect("dashboard")


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


# ── Page views ────────────────────────────────────────────────────────────────

KPIS = [
    {"label": "Active Agents",   "value": "16",    "color": "#2dd4bf", "sub": "across 4 domains"},
    {"label": "Incidents Today", "value": "7",     "color": "#fbbf24", "sub": "3 auto-healed"},
    {"label": "SLO Compliance",  "value": "99.1%", "color": "#34d399", "sub": "last 24 hours"},
    {"label": "A2A Messages",    "value": "1,247", "color": "#a78bfa", "sub": "since startup"},
]

AGENT_TYPES = [
    {"id": "perceiver",  "label": "Perceiver",  "color": "#2dd4bf", "color2": "#06b6d4"},
    {"id": "planner",    "label": "Planner",    "color": "#a78bfa", "color2": "#8b5cf6"},
    {"id": "recoverer",  "label": "Recoverer",  "color": "#34d399", "color2": "#10b981"},
    {"id": "guardian",   "label": "Guardian",   "color": "#f87171", "color2": "#ef4444"},
]
AGENT_INFO = {
    "perceiver": {
        "name": "Perceiver Agent", "emoji": "👁",
        "color": "#2dd4bf", "description": "Monitors signals, detects anomalies, feeds alerts to Planner",
        "stats": [{"label": "Alerts/hr", "value": "12"}, {"label": "Latency", "value": "87ms"}, {"label": "Accuracy", "value": "98.3%"}],
        "capabilities": ["Signal monitoring", "Anomaly detection", "HRV analysis", "Latency tracking", "A2A messaging"],
        "messages": [
            {"type": "anomaly.detected", "msg": "RSRP dropped to −94 dBm on Tower-7"},
            {"type": "status.update",    "msg": "All sensors nominal — 87ms round-trip"},
            {"type": "latency.spike",    "msg": "Edge node latency 340ms — escalating"},
            {"type": "heartbeat",        "msg": "Heartbeat OK — peers responding"},
        ],
    },
    "planner": {
        "name": "Planner Agent", "emoji": "🧠",
        "color": "#a78bfa", "description": "Generates action plans using LLM, coordinates recovery",
        "stats": [{"label": "Plans/hr", "value": "8"}, {"label": "LLM Model", "value": "Llama"}, {"label": "Success", "value": "96.7%"}],
        "capabilities": ["LLM reasoning", "Action planning", "Resource allocation", "Multi-agent coordination", "SLO optimisation"],
        "messages": [
            {"type": "action.plan",      "msg": "Failover plan generated — target Tower-9"},
            {"type": "capability.query", "msg": "Querying Recoverer capabilities"},
            {"type": "action.plan",      "msg": "Auto-scale +3 replicas dispatched"},
            {"type": "status.update",    "msg": "Plan executed — SLO restored"},
        ],
    },
    "recoverer": {
        "name": "Recoverer Agent", "emoji": "🔧",
        "color": "#34d399", "description": "Executes healing actions, restores SLOs, reports outcomes",
        "stats": [{"label": "Heals/hr", "value": "5"}, {"label": "MTTR", "value": "2.3s"}, {"label": "SLO", "value": "99.1%"}],
        "capabilities": ["Pod restart", "Beam steering", "Traffic rerouting", "Rollback", "Failover execution"],
        "messages": [
            {"type": "heal.complete", "msg": "Pod restarted — SLO 99.2% restored"},
            {"type": "heal.complete", "msg": "Beam steering applied — Tower-7 recovered"},
            {"type": "status.update", "msg": "Rollback complete — v2.2 stable"},
            {"type": "heal.complete", "msg": "Failover completed — SLO 99.3%"},
        ],
    },
    "guardian": {
        "name": "Guardian Agent", "emoji": "🛡",
        "color": "#f87171", "description": "Monitors security, blocks threats, enforces A2A integrity",
        "stats": [{"label": "Blocks/hr", "value": "3"}, {"label": "False+", "value": "0.2%"}, {"label": "Uptime", "value": "100%"}],
        "capabilities": ["Injection detection", "A2A signature verification", "Rate limiting", "Device quarantine", "Audit logging"],
        "messages": [
            {"type": "threat.blocked", "msg": "SQL injection intercepted — source quarantined"},
            {"type": "threat.blocked", "msg": "Spoofed A2A message rejected"},
            {"type": "heartbeat",      "msg": "Security perimeter nominal"},
            {"type": "threat.blocked", "msg": "DDoS mitigated — traffic shaped"},
        ],
    },
}

DOMAIN_TABS = [
    {"id": "5g",      "label": "5G Self-Healing", "color": "#2dd4bf", "color2": "#06b6d4"},
    {"id": "cloud",   "label": "Cloud Cost",       "color": "#60a5fa", "color2": "#3b82f6"},
    {"id": "icu",     "label": "ICU Monitoring",   "color": "#f472b6", "color2": "#ec4899"},
    {"id": "network", "label": "Network",           "color": "#fb923c", "color2": "#f97316"},
]
DOMAIN_INFO = {
    "5g":      {"label": "5G Self-Healing",  "emoji": "📡", "color": "#2dd4bf", "color2": "#06b6d4", "health": 94, "description": "Autonomous 5G network healing — RSRP, RSRQ, handoff optimisation", "stats": [{"label": "Towers", "value": "48"}, {"label": "Uptime", "value": "99.1%"}, {"label": "Heals", "value": "12"}], "events": [{"type": "anomaly.detected", "msg": "RSRP −94 dBm on Tower-7"}, {"type": "heal.complete", "msg": "Beam steering applied — restored"}, {"type": "status.update", "msg": "All towers nominal"}]},
    "cloud":   {"label": "Cloud Cost",       "emoji": "☁️", "color": "#60a5fa", "color2": "#3b82f6", "health": 87, "description": "Cloud resource optimisation — cost management, auto-scaling, SLO enforcement", "stats": [{"label": "Clusters", "value": "6"}, {"label": "Cost Save", "value": "18%"}, {"label": "SLO", "value": "99.3%"}], "events": [{"type": "scale.out", "msg": "CPU 89% — +3 replicas"}, {"type": "cost.alert", "msg": "Spend +12% this week"}, {"type": "heal.complete", "msg": "Memory leak patched"}]},
    "icu":     {"label": "ICU Monitoring",   "emoji": "🏥", "color": "#f472b6", "color2": "#ec4899", "health": 91, "description": "Critical care patient monitoring — HRV, vitals, equipment fault detection", "stats": [{"label": "Patients", "value": "24"}, {"label": "Alerts", "value": "3"}, {"label": "Response", "value": "1.2s"}], "events": [{"type": "anomaly.detected", "msg": "HRV spike Ward-3A"}, {"type": "device.fault", "msg": "Vitals monitor offline"}, {"type": "heal.complete", "msg": "Failsafe activated — nurses notified"}]},
    "network": {"label": "Network",          "emoji": "⚡", "color": "#fb923c", "color2": "#f97316", "health": 96, "description": "Edge network latency management and traffic rerouting", "stats": [{"label": "Edge Nodes", "value": "14"}, {"label": "Latency", "value": "95ms"}, {"label": "Uptime", "value": "99.6%"}], "events": [{"type": "latency.spike", "msg": "Edge-SG3 340ms — rerouting"}, {"type": "heal.complete", "msg": "Rerouted via Tokyo — 95ms"}, {"type": "status.update", "msg": "Mesh optimised — 14 nodes"}]},
}

SECURITY_ATTACKS = [
    {"id": "injection", "label": "SQL Injection",    "desc": "Attack cloud API endpoint with injection payload", "color": "#f87171"},
    {"id": "spoof",     "label": "A2A Spoof",        "desc": "Send forged agent message as Perceiver-1",         "color": "#fb923c"},
    {"id": "ddos",      "label": "DDoS Flood",       "desc": "Simulate 500 req/s flood on /api/agents/",         "color": "#fbbf24"},
]

DOMAINS_LIST = [
    {"id": "telecom", "label": "Telecom / 5G", "color": "#2dd4bf"},
    {"id": "cloud",   "label": "Cloud",        "color": "#60a5fa"},
    {"id": "icu",     "label": "ICU",          "color": "#f472b6"},
    {"id": "edge",    "label": "Edge",         "color": "#fb923c"},
]

@_require_auth
def dashboard(request):
    return render(request, "frontend/dashboard.html", _ctx(request, "dashboard", kpis=KPIS))

@_require_auth
def a2a_chat(request):
    return render(request, "frontend/a2a_chat.html", _ctx(request, "a2a-chat"))

import json as _json

@_require_auth
def agents(request, agent_type="perceiver"):
    if agent_type not in AGENT_INFO:
        agent_type = "perceiver"
    info = AGENT_INFO[agent_type]
    return render(request, "frontend/agents.html", _ctx(
        request, "agents",
        agent_type=agent_type,
        agent_types=AGENT_TYPES,
        agent_info=info,
        agent_messages=_json.dumps(info["messages"]),
    ))

@_require_auth
def domains(request, domain="5g"):
    if domain not in DOMAIN_INFO:
        domain = "5g"
    info = DOMAIN_INFO[domain]
    return render(request, "frontend/domains.html", _ctx(
        request, "domains",
        domain=domain,
        domain_tabs=DOMAIN_TABS,
        domain_info=info,
        domain_events=_json.dumps(info["events"]),
    ))

@_require_auth
def incidents(request):
    return render(request, "frontend/incidents.html", _ctx(
        request, "incidents",
        sev_options=[("critical", "#f87171"), ("warning", "#fbbf24"), ("info", "#a78bfa"), ("ok", "#34d399")],
    ))

@_require_auth
def audit_log(request):
    return render(request, "frontend/audit_log.html", _ctx(request, "audit-log"))

@_require_auth
def context_graph(request):
    return render(request, "frontend/context_graph.html", _ctx(request, "context-graph"))

@_require_auth
def security(request):
    return render(request, "frontend/security.html", _ctx(
        request, "security",
        attacks=SECURITY_ATTACKS,
    ))

@_require_auth
def settings_view(request):
    return render(request, "frontend/settings.html", _ctx(request, "settings"))

@_require_auth
def self_healing(request):
    return render(request, "frontend/self_healing.html", _ctx(
        request, "self-healing",
        domains_list=DOMAINS_LIST,
    ))

@_require_auth
def map_view(request):
    return render(request, "frontend/map.html", _ctx(
        request, "map",
        domain_colors=[("telecom", "#2dd4bf"), ("cloud", "#60a5fa"), ("icu", "#f472b6"), ("edge", "#fb923c")],
    ))
