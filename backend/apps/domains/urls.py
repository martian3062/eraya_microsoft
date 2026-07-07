from django.urls import path
from . import views

urlpatterns = [
    path("", views.domain_list, name="domain-list"),
    path("providers/status/", views.provider_status, name="provider-status"),
    path("rag/ingest/", views.rag_ingest, name="rag-ingest"),
    path("rag/query/", views.rag_query, name="rag-query"),
    path("casper_defi/dashboard/", views.casper_dashboard, name="casper-dashboard"),
    path("casper_defi/portfolio/", views.casper_portfolio, name="casper-portfolio"),
    path("casper_defi/yields/", views.casper_yields, name="casper-yields"),
    path("casper_defi/consensus/", views.casper_consensus, name="casper-consensus"),
    path("casper_defi/reputation/", views.casper_reputation, name="casper-reputation"),
    path("casper_defi/transactions/", views.casper_transactions, name="casper-transactions"),
    path("casper_defi/threats/", views.casper_threats, name="casper-threats"),
    path("casper_defi/onchain/", views.casper_onchain, name="casper-onchain"),
    path("casper_defi/swarm-chat/", views.casper_swarm_chat, name="casper-swarm-chat"),
    path("casper_defi/pay/", views.casper_pay, name="casper-pay"),
    path("casper_defi/copilot/", views.casper_copilot, name="casper-copilot"),
    path("casper_defi/transcribe/", views.casper_transcribe, name="casper-transcribe"),
    path("casper_defi/speak/", views.casper_speak, name="casper-speak"),
    path("casper_defi/market-data/", views.casper_market_data, name="casper-market-data"),
    path("casper_defi/x402/verify/", views.x402_verify, name="casper-x402-verify"),
    path("<str:domain>/status/", views.domain_status, name="domain-status"),
    path("<str:domain>/signals/", views.domain_signals, name="domain-signals"),
    path("<str:domain>/actions/", views.domain_actions, name="domain-actions"),
]
