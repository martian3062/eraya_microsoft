from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from .models import Decision
from rest_framework import serializers


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Decision
        fields = "__all__"


class DecisionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Decision.objects.all()
    serializer_class = DecisionSerializer
    permission_classes = [AllowAny]
    filterset_fields = ["domain", "guardian_approved", "tier_used"]


router = DefaultRouter()
router.register("", DecisionViewSet, basename="decision")

urlpatterns = [path("", include(router.urls))]
