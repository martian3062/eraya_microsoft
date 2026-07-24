"""
The ERAYA quant trading engine.

The swarm trades CSPR/USD with its own quant ensemble (SMA crossover, RSI,
Bollinger, momentum, volatility targeting) on LIVE exchange prices. The user
sets exactly one input — the risk factor (1-10) — and every policy limit
(position cap, stop-loss, take-profit, trade budget, drawdown halt) derives
from it. Fills are paper (testnet has no liquid DEX) at real prices; every
executed trade is settled as a real Casper testnet transfer whose transfer-id
encodes the trade id, giving each trade a cspr.live proof link.

Archetype mapping per tick: Perceiver reads the market, Planner scores the
ensemble and proposes, Guardian enforces the risk envelope, Recoverer executes
and settles on-chain.
"""
from __future__ import annotations

import logging
import math
import statistics
import threading
import time
from collections import deque

from . import feed

logger = logging.getLogger("eraya.quant.engine")

TICK_INTERVAL_S = 30
FEE_RATE = 0.001          # 10 bps per side
SLIPPAGE = 0.0005         # 5 bps
MIN_NOTIONAL_USD = 50.0
SETTLE_AMOUNT_MOTES = 2_500_000_000  # 2.5 CSPR min native transfer


def risk_profile(risk: int) -> dict:
    """Derive the full trading policy from the single user-set risk dial."""
    r = max(1, min(10, int(risk)))
    t = (r - 1) / 9.0

    def lerp(a, b):
        return a + (b - a) * t

    label = ("Conservative" if r <= 3 else "Balanced" if r <= 6
             else "Aggressive" if r <= 8 else "Degen")
    return {
        "risk": r,
        "label": label,
        "signal_threshold": round(lerp(0.55, 0.25), 3),
        "max_position_pct": round(lerp(0.05, 0.60), 3),
        "stop_loss_pct": round(lerp(0.012, 0.06), 4),
        "take_profit_pct": round(lerp(0.02, 0.10), 4),
        "max_trades_day": int(round(lerp(4, 40))),
        "cooldown_s": int(round(lerp(600, 45))),
        "drawdown_halt_pct": round(lerp(0.02, 0.12), 4),
        "vol_target": round(lerp(0.6, 2.5), 2),
    }


def _sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None


def _rsi(closes, n=14):
    if len(closes) < n + 1:
        return None
    gains = losses = 0.0
    for prev, cur in zip(closes[-n - 1:-1], closes[-n:]):
        d = cur - prev
        gains += max(d, 0.0)
        losses += max(-d, 0.0)
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - 100.0 / (1.0 + rs)


def compute_indicators(closes: list[float]) -> dict:
    """Quant ensemble -> score in [-1, +1]. Positive = buy pressure."""
    price = closes[-1]
    sma9, sma26, sma20 = _sma(closes, 9), _sma(closes, 26), _sma(closes, 20)
    rsi = _rsi(closes)

    cross = 0.0
    if sma9 and sma26:
        cross = math.copysign(min(abs(sma9 - sma26) / price / 0.004, 1.0),
                              sma9 - sma26)

    rsi_score = max(-1.0, min(1.0, (50.0 - rsi) / 25.0)) if rsi is not None else 0.0

    boll = 0.0
    boll_z = None
    if sma20 and len(closes) >= 20:
        std20 = statistics.pstdev(closes[-20:])
        if std20 > 0:
            boll_z = (price - sma20) / (2 * std20)
            boll = -max(-1.0, min(1.0, boll_z))

    mom = 0.0
    roc10 = None
    if len(closes) >= 11:
        roc10 = (closes[-1] - closes[-11]) / closes[-11]
        mom = max(-1.0, min(1.0, roc10 / 0.01))

    vol_ann = None
    if len(closes) >= 61:
        rets = [math.log(b / a) for a, b in zip(closes[-61:-1], closes[-60:])
                if a > 0 and b > 0]
        if len(rets) >= 2:
            vol_ann = statistics.pstdev(rets) * math.sqrt(525_600)

    score = 0.30 * cross + 0.25 * rsi_score + 0.20 * boll + 0.25 * mom
    return {
        "price": price,
        "sma9": sma9, "sma26": sma26,
        "rsi14": round(rsi, 1) if rsi is not None else None,
        "boll_z": round(boll_z, 2) if boll_z is not None else None,
        "roc10_pct": round(roc10 * 100, 3) if roc10 is not None else None,
        "vol_annual_pct": round(vol_ann * 100, 1) if vol_ann is not None else None,
        "components": {"crossover": round(cross, 3), "rsi": round(rsi_score, 3),
                       "bollinger": round(boll, 3), "momentum": round(mom, 3)},
        "score": round(score, 3),
    }


class QuantEngine:
    """Singleton paper-ledger + real-price + real-settlement trading engine."""

    def __init__(self):
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._equity_curve: deque = deque(maxlen=1440)
        self._activity: deque = deque(maxlen=60)
        self._last_tick: dict = {}
        self._loaded = False

    # ── persistence ─────────────────────────────────────────────────────
    def _state(self):
        from apps.trading.models import QuantEngineState
        state, _ = QuantEngineState.objects.get_or_create(pk=1)
        return state

    def _log(self, role: str, text: str):
        self._activity.appendleft(
            {"ts": time.time(), "role": role, "text": text})

    # ── controls ────────────────────────────────────────────────────────
    def set_risk(self, risk: int) -> dict:
        with self._lock:
            state = self._state()
            state.risk = max(1, min(10, int(risk)))
            state.save(update_fields=["risk", "updated_at"])
            policy = risk_profile(state.risk)
            self._log("Guardian",
                      f"risk envelope set to {state.risk}/10 ({policy['label']}) — "
                      f"max position {policy['max_position_pct']:.0%}, "
                      f"SL {policy['stop_loss_pct']:.1%}, TP {policy['take_profit_pct']:.1%}")
            return policy

    def set_autopilot(self, enabled: bool) -> bool:
        with self._lock:
            state = self._state()
            state.autopilot = bool(enabled)
            state.save(update_fields=["autopilot", "updated_at"])
            if enabled:
                self._start_thread()
                self._log("Planner", "autopilot engaged — evaluating every "
                          f"{TICK_INTERVAL_S}s on live market data")
            else:
                self._stop.set()
                self._log("Planner", "autopilot disengaged by operator")
            return state.autopilot

    def reset(self) -> None:
        from apps.trading.models import QuantEngineState, QuantTrade
        with self._lock:
            QuantTrade.objects.all().delete()
            state = self._state()
            state.cash_usd = state.start_cash_usd
            state.pos_units = 0.0
            state.avg_entry = 0.0
            state.peak_equity = state.start_cash_usd
            state.day = None
            state.day_start_equity = state.start_cash_usd
            state.day_trades = 0
            state.last_trade_at = 0.0
            state.save()
            self._equity_curve.clear()
            self._log("Recoverer", "paper account reset to "
                      f"${state.start_cash_usd:,.0f}")

    def _start_thread(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="quant-autopilot", daemon=True)
        self._thread.start()

    def _run(self):
        from django.db import close_old_connections
        logger.info("quant autopilot thread started")
        while not self._stop.is_set():
            try:
                close_old_connections()
                if not self._state().autopilot:
                    break
                self.tick()
            except Exception as exc:
                logger.exception("autopilot tick failed: %s", exc)
            self._stop.wait(TICK_INTERVAL_S)
        logger.info("quant autopilot thread stopped")

    def ensure_autopilot(self):
        """Re-arm the thread after a process restart if autopilot was on."""
        try:
            if self._state().autopilot:
                self._start_thread()
        except Exception:
            pass  # during migrate the table may not exist yet

    # ── trading ─────────────────────────────────────────────────────────
    def tick(self, manual: bool = False) -> dict:
        with self._lock:
            return self._tick_locked(manual)

    def _tick_locked(self, manual: bool) -> dict:
        import datetime as dt

        state = self._state()
        policy = risk_profile(state.risk)
        market = feed.get_candles()
        closes = [c["c"] for c in market["candles"]]
        if len(closes) < 30:
            return {"acted": False, "reason": "insufficient market data"}
        ind = compute_indicators(closes)
        price = ind["price"]

        self._log("Perceiver",
                  f"CSPR ${price:.6f} via {market['source']} — RSI {ind['rsi14']}, "
                  f"vol {ind['vol_annual_pct']}%, score {ind['score']:+.2f}")

        # day rollover
        today = dt.date.today()
        equity = state.cash_usd + state.pos_units * price
        if state.day != today:
            state.day = today
            state.day_trades = 0
            state.day_start_equity = equity

        self._equity_curve.append({"t": time.time(), "eq": round(equity, 2)})
        state.peak_equity = max(state.peak_equity, equity)

        decision = self._decide(state, policy, ind, price)
        self._last_tick = {
            "ts": time.time(), "manual": manual, "price": price,
            "score": ind["score"], "decision": decision,
        }

        if decision["intent"] in ("BUY", "SELL") and decision["approved"]:
            self._execute(state, policy, decision, ind, price)
        state.save()
        return self._last_tick

    def _decide(self, state, policy, ind, price) -> dict:
        score, threshold = ind["score"], policy["signal_threshold"]
        intent, why = "HOLD", []

        if state.pos_units > 0:
            stop = state.avg_entry * (1 - policy["stop_loss_pct"])
            target = state.avg_entry * (1 + policy["take_profit_pct"])
            if price <= stop:
                intent, why = "SELL", [f"stop-loss hit (${stop:.6f})"]
            elif price >= target:
                intent, why = "SELL", [f"take-profit hit (${target:.6f})"]
            elif score <= -threshold * 0.8:
                intent, why = "SELL", [f"exit signal {score:+.2f}"]
        elif score >= threshold:
            intent = "BUY"
            comp = ind["components"]
            why = [f"{k} {v:+.2f}" for k, v in comp.items() if abs(v) >= 0.15]

        if intent == "HOLD":
            return {"intent": "HOLD", "approved": False, "why": why,
                    "guardian": {"verdict": "N/A", "checks": []}}

        self._log("Planner", f"proposes {intent} — " + ", ".join(why))

        equity = state.cash_usd + state.pos_units * price
        drawdown_day = ((state.day_start_equity - equity)
                        / state.day_start_equity if state.day_start_equity else 0.0)
        checks = [
            ("trade budget",
             state.day_trades < policy["max_trades_day"],
             f"{state.day_trades}/{policy['max_trades_day']} today"),
            ("cooldown",
             time.time() - state.last_trade_at >= policy["cooldown_s"],
             f"{policy['cooldown_s']}s between trades"),
            ("daily drawdown",
             drawdown_day < policy["drawdown_halt_pct"],
             f"{drawdown_day:.1%} of {policy['drawdown_halt_pct']:.1%} halt"),
        ]
        approved = all(ok for _, ok, _ in checks)
        verdict = "APPROVED" if approved else "REJECTED"
        failed = [name for name, ok, _ in checks if not ok]
        self._log("Guardian",
                  f"{verdict} {intent}" + (f" — blocked by {', '.join(failed)}"
                                           if failed else " — within risk envelope"))
        return {"intent": intent, "approved": approved, "why": why,
                "guardian": {"verdict": verdict,
                             "checks": [{"name": n, "ok": ok, "detail": d}
                                        for n, ok, d in checks]}}

    def _execute(self, state, policy, decision, ind, price):
        from apps.trading.models import QuantTrade

        equity = state.cash_usd + state.pos_units * price
        if decision["intent"] == "BUY":
            vol = (ind["vol_annual_pct"] or 100.0) / 100.0
            vol_scalar = min(1.0, policy["vol_target"] / vol) if vol > 0 else 1.0
            notional = min(equity * policy["max_position_pct"] * vol_scalar,
                           state.cash_usd)
            if notional < MIN_NOTIONAL_USD:
                self._log("Guardian", f"BUY skipped — notional ${notional:.0f} "
                          f"below ${MIN_NOTIONAL_USD:.0f} floor")
                return
            fill = price * (1 + SLIPPAGE)
            qty = notional / fill
            fee = notional * FEE_RATE
            new_units = state.pos_units + qty
            state.avg_entry = ((state.avg_entry * state.pos_units + fill * qty)
                               / new_units)
            state.pos_units = new_units
            state.cash_usd -= notional + fee
            pnl = None
        else:  # SELL closes the whole position
            qty = state.pos_units
            if qty <= 0:
                return
            fill = price * (1 - SLIPPAGE)
            notional = qty * fill
            fee = notional * FEE_RATE
            pnl = (fill - state.avg_entry) * qty - fee
            state.cash_usd += notional - fee
            state.pos_units = 0.0
            state.avg_entry = 0.0

        state.day_trades += 1
        state.last_trade_at = time.time()

        trade = QuantTrade.objects.create(
            ts=time.time(), side=decision["intent"], qty=round(qty, 2),
            price=fill, notional_usd=round(notional, 2), fee_usd=round(fee, 4),
            pnl_usd=round(pnl, 4) if pnl is not None else None,
            score=ind["score"],
            reason={"why": decision["why"], "indicators": {
                "rsi14": ind["rsi14"], "boll_z": ind["boll_z"],
                "roc10_pct": ind["roc10_pct"],
                "vol_annual_pct": ind["vol_annual_pct"],
                "components": ind["components"]}},
            guardian=decision["guardian"], risk=state.risk,
            settle_status="pending" if self._settlement_enabled() else "unsigned",
        )
        self._log("Recoverer",
                  f"executed {trade.side} {qty:,.0f} CSPR @ ${fill:.6f} "
                  f"(${notional:,.2f})"
                  + (f" — realized {pnl:+,.2f} USD" if pnl is not None else ""))
        if self._settlement_enabled():
            threading.Thread(target=self._settle, args=(trade.pk,),
                             daemon=True).start()

    # ── on-chain settlement ─────────────────────────────────────────────
    @staticmethod
    def _settlement_enabled() -> bool:
        from core.casper.anchor import anchoring_enabled
        return anchoring_enabled()

    def _settle(self, trade_pk: int):
        """Settle a trade as a real Casper testnet transfer (memo = trade id)."""
        import os

        from django.db import close_old_connections

        from core.casper.onchain import send_transfer
        close_old_connections()
        from apps.trading.models import QuantTrade
        try:
            trade = QuantTrade.objects.get(pk=trade_pk)
            target = os.environ.get(
                "CASPER_ANCHOR_RECIPIENT",
                "0202f47d42c6d9b836fe93777489699ae33f12a924a8f2520ace7bb84226a2e4bf69")
            res = send_transfer(target, SETTLE_AMOUNT_MOTES, memo_id=trade_pk)
            if res.get("ok"):
                trade.settle_status = "settled"
                trade.settle_tx = res.get("tx") or ""
                trade.explorer_url = res.get("explorer_url") or ""
                self._log("Recoverer",
                          f"trade #{trade_pk} settled on-chain — {trade.settle_tx[:16]}…")
            else:
                trade.settle_status = "failed"
                self._log("Guardian",
                          f"trade #{trade_pk} settlement failed: {res.get('error')}")
            trade.save(update_fields=["settle_status", "settle_tx", "explorer_url"])
        except Exception as exc:
            logger.warning("settlement thread failed: %s", exc)

    # ── reporting ───────────────────────────────────────────────────────
    def status(self) -> dict:
        from apps.trading.models import QuantTrade
        with self._lock:
            state = self._state()
            policy = risk_profile(state.risk)
            market = feed.get_candles()
            closes = [c["c"] for c in market["candles"]]
            ind = compute_indicators(closes) if len(closes) >= 30 else {}
            price = ind.get("price") or (closes[-1] if closes else 0.0)

            equity = state.cash_usd + state.pos_units * price
            unrealized = ((price - state.avg_entry) * state.pos_units
                          if state.pos_units else 0.0)
            trades = list(QuantTrade.objects.order_by("-ts")[:30])
            sells = [t for t in trades if t.pnl_usd is not None]
            wins = sum(1 for t in sells if t.pnl_usd > 0)
            realized = sum(t.pnl_usd for t in sells)
            drawdown = ((state.peak_equity - equity) / state.peak_equity
                        if state.peak_equity else 0.0)

            threshold = policy["signal_threshold"]
            score = ind.get("score", 0.0)
            verdict = ("BUY zone" if score >= threshold else
                       "SELL zone" if score <= -threshold else "HOLD")

            return {
                "engine": {
                    "autopilot": state.autopilot,
                    "thread_alive": bool(self._thread and self._thread.is_alive()),
                    "tick_interval_s": TICK_INTERVAL_S,
                    "last_tick": self._last_tick,
                    "feed": {"source": market["source"], "live": market["live"]},
                    "settlement": {"enabled": self._settlement_enabled(),
                                   "network": "casper-test",
                                   "amount_cspr": SETTLE_AMOUNT_MOTES / 1e9},
                },
                "risk": policy,
                "account": {
                    "start_cash_usd": state.start_cash_usd,
                    "cash_usd": round(state.cash_usd, 2),
                    "pos_units": round(state.pos_units, 2),
                    "avg_entry": state.avg_entry,
                    "equity_usd": round(equity, 2),
                    "unrealized_usd": round(unrealized, 2),
                    "realized_usd": round(realized, 2),
                    "win_rate_pct": round(100 * wins / len(sells), 1) if sells else None,
                    "closed_trades": len(sells),
                    "trades_today": state.day_trades,
                    "drawdown_pct": round(100 * drawdown, 2),
                },
                "signal": {**ind, "threshold": threshold, "verdict": verdict},
                "candles": [{"t": c["t"], "c": c["c"]}
                            for c in market["candles"][-120:]],
                "equity_curve": list(self._equity_curve),
                "trades": [self._trade_dict(t) for t in trades],
                "activity": list(self._activity),
            }

    @staticmethod
    def _trade_dict(t) -> dict:
        return {
            "id": t.pk, "ts": t.ts, "side": t.side, "qty": t.qty,
            "price": t.price, "notional_usd": t.notional_usd,
            "fee_usd": t.fee_usd, "pnl_usd": t.pnl_usd, "score": t.score,
            "reason": t.reason, "guardian": t.guardian, "risk": t.risk,
            "settle_status": t.settle_status, "settle_tx": t.settle_tx,
            "explorer_url": t.explorer_url,
        }


_ENGINE: QuantEngine | None = None
_ENGINE_LOCK = threading.Lock()


def get_engine() -> QuantEngine:
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = QuantEngine()
            _ENGINE.ensure_autopilot()
        return _ENGINE
