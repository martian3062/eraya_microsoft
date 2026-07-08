from django.db import models


class CapOrder(models.Model):
    """One CAP order (either direction). Mirrors Negotiate→Lock→Deliver→Clear."""

    DIRECTION = [("sell", "Sell"), ("buy", "Buy")]
    STATUS = [
        ("negotiated", "Negotiated"),
        ("locked", "Locked"),
        ("delivered", "Delivered"),
        ("cleared", "Cleared"),
        ("disputed", "Disputed"),
    ]

    order_id = models.CharField(max_length=64, unique=True)
    direction = models.CharField(max_length=8, choices=DIRECTION)
    service = models.CharField(max_length=96)          # kavacha | panjshir | external:<cap>
    counterparty = models.CharField(max_length=128, blank=True, default="")
    status = models.CharField(max_length=16, choices=STATUS, default="negotiated")
    verdict = models.CharField(max_length=32, blank=True, default="")
    usdc = models.FloatField(default=0.0)
    pts_delta = models.IntegerField(default=0)
    audit_id = models.CharField(max_length=64, blank=True, default="")
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.direction}] {self.service} {self.status} ({self.usdc} USDC)"

    def as_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "direction": self.direction,
            "service": self.service,
            "counterparty": self.counterparty,
            "status": self.status,
            "verdict": self.verdict,
            "usdc": self.usdc,
            "pts_delta": self.pts_delta,
            "audit_id": self.audit_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
