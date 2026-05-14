from django.db import models


class Incident(models.Model):
    SEVERITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("critical", "Critical"),
    ]
    STATUS_CHOICES = [
        ("open", "Open"),
        ("investigating", "Investigating"),
        ("mitigating", "Mitigating"),
        ("resolved", "Resolved"),
    ]

    incident_id = models.CharField(max_length=32, unique=True)
    title = models.CharField(max_length=256)
    domain = models.CharField(max_length=64)
    severity = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default="medium")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="open")
    description = models.TextField(blank=True)
    affected_agents = models.JSONField(default=list)
    root_cause = models.TextField(blank=True)
    recovery_plan = models.JSONField(default=dict)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-detected_at"]
        indexes = [models.Index(fields=["domain", "status"])]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title}"


class IncidentTimeline(models.Model):
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="timeline")
    event_type = models.CharField(max_length=64)  # detected | agent_action | veto | resolved
    actor = models.CharField(max_length=64, blank=True)
    description = models.TextField()
    payload = models.JSONField(default=dict)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["occurred_at"]
