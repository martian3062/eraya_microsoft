"""
WebSocket consumer — streams live agent events to the operator console.

Channels:
  eraya.swarm          — all agents, all domains (dashboard)
  eraya.domain.<name>  — domain-specific stream
  eraya.a2a            — live A2A message feed
  eraya.guardian       — Guardian vetoes + audit events
"""
import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

logger = logging.getLogger("eraya.ws")


class ErayaConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.domain = self.scope["url_route"]["kwargs"].get("domain", "swarm")
        self.channel_group = f"eraya.{self.domain}"

        await self.channel_layer.group_add(self.channel_group, self.channel_name)

        # All consoles also join the swarm-wide channel
        if self.domain != "swarm":
            await self.channel_layer.group_add("eraya.swarm", self.channel_name)

        await self.accept()
        logger.info("WS connected: %s → %s", self.channel_name, self.channel_group)

        await self.send(json.dumps({
            "type": "connected",
            "channel": self.channel_group,
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.channel_group, self.channel_name)
        if self.domain != "swarm":
            await self.channel_layer.group_discard("eraya.swarm", self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            data = json.loads(text_data)
            event_type = data.get("type")

            if event_type == "ping":
                await self.send(json.dumps({"type": "pong"}))

            elif event_type == "subscribe":
                extra_channel = f"eraya.{data.get('channel', 'swarm')}"
                await self.channel_layer.group_add(extra_channel, self.channel_name)
                await self.send(json.dumps({"type": "subscribed", "channel": extra_channel}))

            elif event_type == "action.request":
                # Additive: verify HMAC signature on inbound A2A delegation messages.
                # Uses verify_a2a_message() — same function the security demo uses,
                # so the test proves the real path, not a copy.
                from core.a2a.verification import verify_a2a_message
                presented_sig = data.get("signature", "")
                # Strip the envelope "type" key before verifying the message body
                message_body = {k: v for k, v in data.items() if k not in ("type", "signature")}
                if not presented_sig or not verify_a2a_message(message_body, presented_sig):
                    logger.warning(
                        "WS A2A delegation from '%s' rejected: hmac_mismatch",
                        data.get("from_agent", "unknown"),
                    )
                    await self.send(json.dumps({
                        "type": "error",
                        "code": "hmac_mismatch",
                        "detail": "invalid or missing A2A signature",
                    }))
                    return
                # Valid — route to the A2A bus
                from core.a2a.bus import get_bus
                from core.a2a.schemas import A2AMessage
                try:
                    msg = A2AMessage(**{k: v for k, v in data.items() if k != "type"})
                    get_bus().publish(msg)
                    await self.send(json.dumps({"type": "ack", "message_id": msg.message_id}))
                except Exception as exc:
                    logger.warning("A2A routing error: %s", exc)

        except json.JSONDecodeError:
            pass

    # ─── Channel layer event handlers ─────────────────────────────────────────

    async def agent_status(self, event):
        await self.send(json.dumps({"type": "agent.status", "data": event["data"]}))

    async def a2a_message(self, event):
        await self.send(json.dumps({"type": "a2a.message", "data": event["data"]}))

    async def guardian_veto(self, event):
        await self.send(json.dumps({"type": "guardian.veto", "data": event["data"]}))

    async def incident_created(self, event):
        await self.send(json.dumps({"type": "incident.created", "data": event["data"]}))

    async def domain_signal(self, event):
        await self.send(json.dumps({"type": "domain.signal", "data": event["data"]}))

    async def perception_result(self, event):
        await self.send(json.dumps({"type": "perception.result", "data": event["data"]}))


# ─── Helper: broadcast from sync Django code ──────────────────────────────────

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_agent_status(agent_data: dict, domain: str = "swarm") -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        f"eraya.{domain}",
        {"type": "agent_status", "data": agent_data},
    )


def broadcast_a2a_message(message_data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        "eraya.swarm",
        {"type": "a2a_message", "data": message_data},
    )


def broadcast_guardian_veto(veto_data: dict) -> None:
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(
        "eraya.guardian",
        {"type": "guardian_veto", "data": veto_data},
    )
    async_to_sync(layer.group_send)(
        "eraya.swarm",
        {"type": "guardian_veto", "data": veto_data},
    )
