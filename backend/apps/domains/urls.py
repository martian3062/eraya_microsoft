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
    path("<str:domain>/status/", views.domain_status, name="domain-status"),
    path("<str:domain>/signals/", views.domain_signals, name="domain-signals"),
    path("<str:domain>/actions/", views.domain_actions, name="domain-actions"),
]
