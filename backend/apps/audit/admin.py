from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["record_id", "agent_id", "domain", "verdict", "timestamp", "reviewed"]
    list_filter = ["verdict", "domain", "reviewed"]
    readonly_fields = ["record_id", "audit_hash", "timestamp"]
