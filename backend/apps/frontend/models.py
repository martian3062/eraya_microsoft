from django.db import models


class SimulationLog(models.Model):
    domain         = models.CharField(max_length=50)
    incident       = models.CharField(max_length=300)
    severity       = models.CharField(max_length=20, default='critical')
    perceiver_msg  = models.TextField()
    perceiver_conf = models.FloatField(default=0.94)
    planner_cause  = models.TextField(default='')
    planner_plan   = models.TextField()
    recoverer_action = models.TextField()
    recoverer_result = models.TextField()
    guardian_sec   = models.TextField(default='')
    guardian_audit = models.TextField()
    incident_id    = models.CharField(max_length=20, default='INC-000')
    groq_model     = models.CharField(max_length=100, default='llama-3.3-70b-versatile')
    groq_powered   = models.BooleanField(default=False)
    heal_time_ms   = models.IntegerField(default=1240)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
