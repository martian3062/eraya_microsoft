from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .models import Incident, IncidentTimeline
from .serializers import IncidentSerializer


class IncidentViewSet(viewsets.ModelViewSet):
    queryset = Incident.objects.prefetch_related("timeline").all()
    serializer_class = IncidentSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["domain", "severity", "status"]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        incident = self.get_object()
        incident.status = "resolved"
        incident.resolved_at = timezone.now()
        if request.data.get("root_cause"):
            incident.root_cause = request.data["root_cause"]
        incident.save()
        IncidentTimeline.objects.create(
            incident=incident,
            event_type="resolved",
            actor=str(request.user),
            description="Incident marked as resolved by operator",
        )
        return Response(IncidentSerializer(incident).data)

    @action(detail=False, methods=["get"])
    def open(self, request):
        qs = Incident.objects.filter(status__in=["open", "investigating", "mitigating"])
        return Response(IncidentSerializer(qs, many=True).data)
