from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentInstanceViewSet, AgentDecisionViewSet, A2AMessageLogViewSet, ModelRegistryView

router = DefaultRouter()
router.register("instances", AgentInstanceViewSet, basename="agent")
router.register("decisions", AgentDecisionViewSet, basename="decision")
router.register("messages", A2AMessageLogViewSet, basename="a2a-message")

urlpatterns = [
    path("", include(router.urls)),
    path("models/", ModelRegistryView.as_view(), name="model-registry"),
]
