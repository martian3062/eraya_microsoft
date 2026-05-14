from django.contrib import admin
from .models import Incident, IncidentTimeline


class TimelineInline(admin.TabularInline):
    model = IncidentTimeline
    extra = 0
    readonly_fields = ["occurred_at"]


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ["incident_id", "title", "domain", "severity", "status", "detected_at"]
    list_filter = ["domain", "severity", "status"]
    inlines = [TimelineInline]
