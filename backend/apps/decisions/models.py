from django.db import models


class Decision(models.Model):
    decision_id = models.CharField(max_length=32, unique=True)
    domain = models.CharField(max_length=64)
    perceiver_id = models.CharField(max_length=64)
    planner_id = models.CharField(max_length=64)
    guardian_id = models.CharField(max_length=64, blank=True)
    perception_result = models.JSONField(default=dict)
    action_plan = models.JSONField(default=dict)
    guardian_approved = models.BooleanField(default=True)
    guardian_reason = models.TextField(blank=True)
    outcome = models.JSONField(default=dict, blank=True)
    reward = models.FloatField(null=True, blank=True)
    tier_used = models.CharField(max_length=8, default="MEDIUM")
    latency_ms = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["domain", "created_at"])]

    def __str__(self):
        return f"Decision {self.decision_id} [{self.domain}] — approved={self.guardian_approved}"
