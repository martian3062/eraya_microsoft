"""
A2ABus — routes messages between agent instances.

Backends:
  redis   — Redis Streams (default for MVP)
  nats    — NATS JetStream (production)
  memory  — in-process dict (dev / test)
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable
from .schemas import A2AMessage, AgentCard

logger = logging.getLogger("eraya.a2a.bus")

MessageHandler = Callable[[A2AMessage], None]

_bus_instance: A2ABus | None = None


def get_bus() -> A2ABus:
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = A2ABus()
    return _bus_instance


class A2ABus:
    """
    Singleton message bus. Agents subscribe to their own queue.
    GuardianAgent subscribes to the veto channel.
    """

    def __init__(self, backend: str = "memory"):
        self._backend = backend
        self._registry: dict[str, AgentCard] = {}       # agent_id → card
        self._handlers: dict[str, list[MessageHandler]] = {}  # agent_id → callbacks
        self._veto_handlers: list[MessageHandler] = []
        self._lock = threading.Lock()
        self._redis_client = None
        self._nats_client = None

        if backend == "redis":
            self._init_redis()
        elif backend == "nats":
            self._init_nats()

    # ─── Agent lifecycle ──────────────────────────────────────────────────────

    def register_agent(self, card: AgentCard) -> None:
        with self._lock:
            self._registry[card.agent_id] = card
        logger.info("Registered agent: %s (%s)", card.agent_id, card.role)

    def deregister_agent(self, agent_id: str) -> None:
        with self._lock:
            self._registry.pop(agent_id, None)
            self._handlers.pop(agent_id, None)

    def subscribe(self, agent_id: str, handler: MessageHandler) -> None:
        with self._lock:
            self._handlers.setdefault(agent_id, []).append(handler)

    def subscribe_veto(self, handler: MessageHandler) -> None:
        self._veto_handlers.append(handler)

    # ─── Capability discovery ─────────────────────────────────────────────────

    def find_agents(
        self,
        capability: str,
        domain: str | None = None,
        trust_tier: str | None = None,
    ) -> list[AgentCard]:
        with self._lock:
            results = []
            for card in self._registry.values():
                if capability not in card.capabilities:
                    continue
                if domain and card.domain != domain:
                    continue
                if trust_tier and card.trust_tier != trust_tier:
                    continue
                results.append(card)
        return results

    # ─── Message routing ──────────────────────────────────────────────────────

    def publish(self, message: A2AMessage) -> bool:
        payload = message.model_dump_json()

        if self._backend == "redis" and self._redis_client:
            return self._redis_publish(message, payload)
        if self._backend == "nats" and self._nats_client:
            return self._nats_publish(message, payload)
        return self._memory_publish(message)

    def _memory_publish(self, message: A2AMessage) -> bool:
        handlers = self._handlers.get(message.to_agent, [])
        if message.message_type == "veto":
            for h in self._veto_handlers:
                self._safe_call(h, message)

        if not handlers:
            logger.debug("No handler for agent '%s'", message.to_agent)
            return False

        for handler in handlers:
            self._safe_call(handler, message)
        return True

    def _redis_publish(self, message: A2AMessage, payload: str) -> bool:
        try:
            stream = f"eraya:a2a:{message.to_agent}"
            self._redis_client.xadd(stream, {"msg": payload}, maxlen=1000)
            return True
        except Exception as exc:
            logger.warning("Redis publish failed: %s", exc)
            return self._memory_publish(message)

    def _nats_publish(self, message: A2AMessage, payload: str) -> bool:
        try:
            subject = f"eraya.a2a.{message.to_agent}"
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                self._nats_client.publish(subject, payload.encode())
            )
            return True
        except Exception as exc:
            logger.warning("NATS publish failed: %s", exc)
            return self._memory_publish(message)

    # ─── Backend init ─────────────────────────────────────────────────────────

    def _init_redis(self) -> None:
        try:
            import redis as redis_lib
            from django.conf import settings
            url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
            self._redis_client = redis_lib.from_url(url, decode_responses=True)
            self._redis_client.ping()
            logger.info("A2ABus: connected to Redis")
        except Exception as exc:
            logger.warning("Redis unavailable, falling back to in-memory: %s", exc)
            self._backend = "memory"

    def _init_nats(self) -> None:
        logger.info("NATS backend selected — connect via async context manager in production")

    @staticmethod
    def _safe_call(handler: MessageHandler, message: A2AMessage) -> None:
        try:
            handler(message)
        except Exception as exc:
            logger.error("Handler error for message %s: %s", message.message_id, exc)

    # ─── Diagnostics ──────────────────────────────────────────────────────────

    def get_registry(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {aid: card.model_dump() for aid, card in self._registry.items()}

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "backend": self._backend,
                "registered_agents": len(self._registry),
                "subscribed_agents": len(self._handlers),
            }
