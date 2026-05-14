from django.contrib import admin
from .models import AgentInstance, AgentDecision, A2AMessageLog


@admin.register(AgentInstance)
class AgentInstanceAdmin(admin.ModelAdmin):
    list_display = ["agent_id", "name", "role", "domain", "status", "current_tier", "last_heartbeat"]
    list_filter = ["role", "domain", "status"]
    search_fields = ["agent_id", "name"]


@admin.register(AgentDecision)
class AgentDecisionAdmin(admin.ModelAdmin):
    list_display = ["agent", "action_id", "domain", "confidence", "guardian_approved", "created_at"]
    list_filter = ["domain", "guardian_approved", "tier_used"]


@admin.register(A2AMessageLog)
class A2AMessageLogAdmin(admin.ModelAdmin):
    list_display = ["from_agent", "to_agent", "message_type", "domain", "timestamp"]
    list_filter = ["message_type", "domain"]
