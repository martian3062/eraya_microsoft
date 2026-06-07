"""
Seed demo AgentInstance rows so the dashboard shows live agents out of the box.
Run once: python manage.py seed_agents
Run again safely: idempotent (uses get_or_create on agent_id).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.agents.models import AgentInstance

SEED = [
    # 5G domain
    dict(agent_id="perceiver-5g-001",  name="Perceiver · 5G",   role="perceiver",  domain="5g",      status="active",      current_tier="HEAVY",  total_calls=1284, avg_latency_ms=87.4,  error_count=2),
    dict(agent_id="planner-5g-001",    name="Planner · 5G",     role="planner",    domain="5g",      status="active",      current_tier="HEAVY",  total_calls=947,  avg_latency_ms=312.8, error_count=1),
    dict(agent_id="recoverer-5g-001",  name="Recoverer · 5G",   role="recoverer",  domain="5g",      status="idle",        current_tier="MEDIUM", total_calls=156,  avg_latency_ms=145.0, error_count=0),
    dict(agent_id="guardian-5g-001",   name="Guardian · 5G",    role="guardian",   domain="5g",      status="active",      current_tier="LIGHT",  total_calls=2103, avg_latency_ms=21.6,  error_count=0),
    # Cloud domain
    dict(agent_id="perceiver-cloud-001", name="Perceiver · Cloud", role="perceiver", domain="cloud",  status="active",    current_tier="MEDIUM", total_calls=881,  avg_latency_ms=64.2,  error_count=0),
    dict(agent_id="planner-cloud-001",   name="Planner · Cloud",   role="planner",   domain="cloud",  status="active",    current_tier="HEAVY",  total_calls=732,  avg_latency_ms=289.5, error_count=3),
    dict(agent_id="recoverer-cloud-001", name="Recoverer · Cloud", role="recoverer", domain="cloud",  status="degraded",  current_tier="MEDIUM", total_calls=214,  avg_latency_ms=188.3, error_count=7),
    dict(agent_id="guardian-cloud-001",  name="Guardian · Cloud",  role="guardian",  domain="cloud",  status="active",    current_tier="LIGHT",  total_calls=1629, avg_latency_ms=18.9,  error_count=0),
    # ICU domain
    dict(agent_id="perceiver-icu-001",   name="Perceiver · ICU",   role="perceiver", domain="icu",    status="active",    current_tier="HEAVY",  total_calls=2417, avg_latency_ms=92.1,  error_count=1),
    dict(agent_id="planner-icu-001",     name="Planner · ICU",     role="planner",   domain="icu",    status="active",    current_tier="HEAVY",  total_calls=1853, avg_latency_ms=401.2, error_count=0),
    dict(agent_id="recoverer-icu-001",   name="Recoverer · ICU",   role="recoverer", domain="icu",    status="active",    current_tier="MEDIUM", total_calls=302,  avg_latency_ms=133.7, error_count=2),
    dict(agent_id="guardian-icu-001",    name="Guardian · ICU",    role="guardian",  domain="icu",    status="active",    current_tier="LIGHT",  total_calls=3104, avg_latency_ms=15.4,  error_count=0),
    # Network domain
    dict(agent_id="perceiver-net-001",   name="Perceiver · Net",   role="perceiver", domain="network", status="active",   current_tier="MEDIUM", total_calls=643,  avg_latency_ms=58.9,  error_count=0),
    dict(agent_id="planner-net-001",     name="Planner · Net",     role="planner",   domain="network", status="idle",     current_tier="MEDIUM", total_calls=418,  avg_latency_ms=245.6, error_count=0),
    dict(agent_id="recoverer-net-001",   name="Recoverer · Net",   role="recoverer", domain="network", status="active",   current_tier="LIGHT",  total_calls=87,   avg_latency_ms=102.3, error_count=1),
    dict(agent_id="guardian-net-001",    name="Guardian · Net",    role="guardian",  domain="network", status="active",   current_tier="LIGHT",  total_calls=971,  avg_latency_ms=19.2,  error_count=0),
]


class Command(BaseCommand):
    help = "Seed demo AgentInstance rows for the dashboard"

    def handle(self, *args, **options):
        created = updated = 0
        now = timezone.now()
        for row in SEED:
            obj, is_new = AgentInstance.objects.get_or_create(
                agent_id=row["agent_id"],
                defaults={**row, "version": "0.1.0", "trust_tier": "high", "last_heartbeat": now},
            )
            if is_new:
                created += 1
            else:
                # refresh metrics each run so demo data looks alive
                for field in ("status", "total_calls", "avg_latency_ms", "error_count"):
                    setattr(obj, field, row[field])
                obj.last_heartbeat = now
                obj.save(update_fields=["status", "total_calls", "avg_latency_ms", "error_count", "last_heartbeat"])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"seed_agents: {created} created, {updated} updated — {len(SEED)} total agents"
        ))
