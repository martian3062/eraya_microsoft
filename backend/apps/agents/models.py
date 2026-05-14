from django.db import models


class AgentInstance(models.Model):
    ROLE_CHOICES = [
        ("perceiver", "Perceiver"),
        ("planner", "Planner"),
        ("recoverer", "Recoverer"),
        ("guardian", "Guardian"),
    ]
    STATUS_CHOICES = [
        ("idle", "Idle"),
        ("active", "Active"),
        ("degraded", "Degraded"),
        ("quarantined", "Quarantined"),
    ]
    TIER_CHOICES = [
        ("HEAVY", "Heavy"),
        ("MEDIUM", "Medium"),
        ("LIGHT", "Light"),
    ]

    agent_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=128)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)
    domain = models.CharField(max_length=64, default="generic")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="idle")
    current_tier = models.CharField(max_length=8, choices=TIER_CHOICES, default="MEDIUM")
    version = models.CharField(max_length=16, default="0.1.0")
    trust_tier = models.CharField(max_length=8, default="high")

    # Metrics (updated periodically)
    total_calls = models.IntegerField(default=0)
    avg_latency_ms = models.FloatField(default=0.0)
    error_count = models.IntegerField(default=0)

    registered_at = models.DateTimeField(auto_now_add=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["role", "domain"]
        indexes = [models.Index(fields=["role", "domain"])]

    def __str__(self):
        return f"{self.name} ({self.domain}) — {self.status}"


class AgentDecision(models.Model):
    agent = models.ForeignKey(AgentInstance, on_delete=models.CASCADE, related_name="decisions")
    domain = models.CharField(max_length=64)
    action_id = models.CharField(max_length=128)
    action_params = models.JSONField(default=dict)
    context_snapshot = models.JSONField(default=dict)
    confidence = models.FloatField(default=0.0)
    tier_used = models.CharField(max_length=8, default="MEDIUM")
    guardian_approved = models.BooleanField(default=True)
    outcome_reward = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["domain", "created_at"])]

    def __str__(self):
        return f"{self.agent.name}: {self.action_id} @ {self.created_at:%H:%M:%S}"


class A2AMessageLog(models.Model):
    message_id = models.CharField(max_length=64, unique=True)
    from_agent = models.CharField(max_length=64)
    to_agent = models.CharField(max_length=64)
    message_type = models.CharField(max_length=32)
    domain = models.CharField(max_length=64, default="generic")
    payload = models.JSONField(default=dict)
    signature = models.CharField(max_length=256, blank=True)
    timestamp = models.DateTimeField()
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["from_agent", "timestamp"])]

    def __str__(self):
        return f"{self.from_agent} → {self.to_agent} [{self.message_type}]"
