from django.urls import path
from .views import AttackSimView, SpoofSimView, CriticReviewView, AnomalyScanView

urlpatterns = [
    path("attack-sim/",    AttackSimView.as_view(),    name="kavacha-attack-sim"),
    path("spoof-sim/",     SpoofSimView.as_view(),     name="kavacha-spoof-sim"),
    path("critic-review/", CriticReviewView.as_view(), name="critic-review"),
    path("anomaly-scan/",  AnomalyScanView.as_view(),  name="anomaly-scan"),
]
