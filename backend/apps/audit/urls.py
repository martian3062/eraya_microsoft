from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets, serializers
from rest_framework.permissions import AllowAny
from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["agent_id", "domain", "verdict"]


router = DefaultRouter()
router.register("", AuditLogViewSet, basename="audit-log")

urlpatterns = [path("", include(router.urls))]
