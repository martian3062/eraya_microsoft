from rest_framework import serializers
from .models import Incident, IncidentTimeline


class IncidentTimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = IncidentTimeline
        fields = "__all__"


class IncidentSerializer(serializers.ModelSerializer):
    timeline = IncidentTimelineSerializer(many=True, read_only=True)

    class Meta:
        model = Incident
        fields = "__all__"
