from django.urls import path
from .views import AttackSimView, SpoofSimView

urlpatterns = [
    path("attack-sim/", AttackSimView.as_view(), name="kavacha-attack-sim"),
    path("spoof-sim/",  SpoofSimView.as_view(),  name="kavacha-spoof-sim"),
]
