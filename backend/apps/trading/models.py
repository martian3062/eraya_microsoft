"""Persistent state for the ERAYA Quant Desk (survives restarts/deploys)."""
from django.db import models


class QuantEngineState(models.Model):
    """Singleton row (pk=1): the paper account + the one user knob (risk)."""

    risk = models.IntegerField(default=3)
    autopilot = models.BooleanField(default=False)
    start_cash_usd = models.FloatField(default=10_000.0)
    cash_usd = models.FloatField(default=10_000.0)
    pos_units = models.FloatField(default=0.0)
    avg_entry = models.FloatField(default=0.0)
    peak_equity = models.FloatField(default=10_000.0)
    day = models.DateField(null=True, blank=True)
    day_start_equity = models.FloatField(default=10_000.0)
    day_trades = models.IntegerField(default=0)
    last_trade_at = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Quant engine state"


class QuantTrade(models.Model):
    """One executed trade: paper fill at a live price + on-chain settlement."""

    ts = models.FloatField(db_index=True)
    side = models.CharField(max_length=4)          # BUY | SELL
    qty = models.FloatField()                      # CSPR units
    price = models.FloatField()                    # fill price USD
    notional_usd = models.FloatField()
    fee_usd = models.FloatField(default=0.0)
    pnl_usd = models.FloatField(null=True, blank=True)  # realized, SELL only
    score = models.FloatField(default=0.0)
    reason = models.JSONField(default=dict)
    guardian = models.JSONField(default=dict)
    risk = models.IntegerField(default=3)
    # unsigned (no key configured) | pending | settled | failed
    settle_status = models.CharField(max_length=16, default="unsigned")
    settle_tx = models.CharField(max_length=128, blank=True, default="")
    explorer_url = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]
