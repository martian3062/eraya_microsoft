from django.urls import path
from . import views

urlpatterns = [
    path("", views.domain_list, name="domain-list"),
    path("<str:domain>/status/", views.domain_status, name="domain-status"),
    path("<str:domain>/signals/", views.domain_signals, name="domain-signals"),
    path("<str:domain>/actions/", views.domain_actions, name="domain-actions"),
]
