from django.contrib import admin
from .models import Decision


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ["decision_id", "domain", "guardian_approved", "reward", "tier_used", "created_at"]
    list_filter = ["domain", "guardian_approved", "tier_used"]
