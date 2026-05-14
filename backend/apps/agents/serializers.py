from rest_framework import serializers
from .models import AgentInstance, AgentDecision, A2AMessageLog


class AgentInstanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentInstance
        fields = "__all__"


class AgentDecisionSerializer(serializers.ModelSerializer):
    agent_name = serializers.CharField(source="agent.name", read_only=True)

    class Meta:
        model = AgentDecision
        fields = "__all__"


class A2AMessageLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = A2AMessageLog
        fields = "__all__"
