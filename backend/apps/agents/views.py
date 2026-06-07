from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.utils import timezone

from .models import AgentInstance, AgentDecision, A2AMessageLog
from .serializers import AgentInstanceSerializer, AgentDecisionSerializer, A2AMessageLogSerializer
from core.a2a.bus import get_bus
from core.agents.local_models import registry_info


class AgentInstanceViewSet(viewsets.ModelViewSet):
    queryset = AgentInstance.objects.all()
    serializer_class = AgentInstanceSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def swarm_status(self, request):
        """Returns live status of all registered agents + A2A bus stats."""
        agents = AgentInstance.objects.all()
        bus = get_bus()
        return Response({
            "agents": AgentInstanceSerializer(agents, many=True).data,
            "a2a_bus": bus.stats(),
            "registry": bus.get_registry(),
        })

    @action(detail=True, methods=["post"])
    def heartbeat(self, request, pk=None):
        agent = self.get_object()
        agent.last_heartbeat = timezone.now()
        agent.save(update_fields=["last_heartbeat"])
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"])
    def quarantine(self, request, pk=None):
        agent = self.get_object()
        agent.status = "quarantined"
        agent.save(update_fields=["status"])
        return Response({"status": "quarantined", "agent_id": agent.agent_id})

    @action(detail=True, methods=["post"])
    def lift_quarantine(self, request, pk=None):
        agent = self.get_object()
        agent.status = "idle"
        agent.save(update_fields=["status"])
        return Response({"status": "idle", "agent_id": agent.agent_id})


class AgentDecisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AgentDecision.objects.select_related("agent").all()
    serializer_class = AgentDecisionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["domain", "agent", "guardian_approved"]


class A2AMessageLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = A2AMessageLog.objects.all()
    serializer_class = A2AMessageLogSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["from_agent", "to_agent", "message_type", "domain"]


class ModelRegistryView(APIView):
    """Return metadata for all registered LLM models (local + Groq)."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"models": registry_info()})
