from django.db import models


class AuditLog(models.Model):
    VERDICT_CHOICES = [
        ("approve", "Approve"),
        ("warn", "Warn"),
        ("block", "Block"),
        ("quarantine", "Quarantine"),
    ]

    record_id = models.CharField(max_length=64, unique=True)
    agent_id = models.CharField(max_length=64)
    domain = models.CharField(max_length=64, default="generic")
    action = models.JSONField(default=dict)
    context = models.JSONField(default=dict)
    verdict = models.CharField(max_length=16, choices=VERDICT_CHOICES, default="approve")
    violations = models.JSONField(default=list)
    audit_hash = models.CharField(max_length=128)   # HMAC-SHA256
    timestamp = models.DateTimeField()
    reviewed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["agent_id", "timestamp"]),
            models.Index(fields=["verdict", "timestamp"]),
        ]

    def __str__(self):
        return f"[{self.verdict.upper()}] {self.agent_id} @ {self.timestamp}"
