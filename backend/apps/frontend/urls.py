from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path("",                        views.login_view,          name="login"),
    path("auth/login/",             views.credential_login,    name="credential_login"),
    path("auth/register/",          views.credential_register, name="credential_register"),
    path("auth/guest/",             views.guest_login,         name="guest_login"),
    path("auth/operator/",          views.operator_login,      name="operator_login"),
    path("auth/google/",            views.google_auth_start,   name="google_auth_start"),
    path("auth/google/callback/",   views.google_auth_callback,name="google_auth_callback"),
    path("auth/logout/",            views.logout_view,         name="logout"),
    # Pages
    path("demo/",                   views.demo,                name="demo"),
    path("demo/dashboard/",         views.demo_dashboard,      name="demo_dashboard"),
    path("demo/anomaly/",           views.demo_anomaly,        name="demo_anomaly"),
    path("demo/security/",          views.demo_security,       name="demo_security"),
    path("demo/critic/",            views.demo_critic,         name="demo_critic"),
    path("demo/x402/",              views.demo_x402,           name="demo_x402"),
    path("demo/updates/",           views.demo_updates,        name="demo_updates"),
    path("demo/analytics/",         views.demo_analytics,      name="demo_analytics"),
    path("demo/swarm/",             views.demo_swarm,          name="demo_swarm"),
    path("demo/kavacha/",           views.demo_kavacha,        name="demo_kavacha"),
    path("demo/wallet/",            views.demo_wallet,         name="demo_wallet"),
    path("demo/trading/",           views.demo_trading,        name="demo_trading"),
    path("demo/eraya-casper.pdf",   views.demo_ppt_pdf,        name="demo_ppt_pdf"),
    path("dashboard/",              views.dashboard,           name="dashboard"),
    path("map/",                    views.map_view,            name="map"),
    path("a2a-chat/",               views.a2a_chat,            name="a2a_chat"),
    path("self-healing/",           views.self_healing,        name="self_healing"),
    path("agents/",                 views.agents,              name="agents_default"),
    path("agents/<str:agent_type>/",views.agents,              name="agents"),
    path("domains/",                views.domains,             name="domains_default"),
    path("domains/<str:domain>/",   views.domains,             name="domains"),
    path("incidents/",              views.incidents,           name="incidents"),
    path("audit-log/",              views.audit_log,           name="audit_log"),
    path("context-graph/",          views.context_graph,       name="context_graph"),
    path("security/",               views.security,            name="security"),
    path("settings/",               views.settings_view,       name="settings"),
    # API
    path("api/fire-drill/",         views.fire_drill,          name="fire_drill"),
    path("api/simulations/",        views.simulation_history,  name="simulation_history"),
]
