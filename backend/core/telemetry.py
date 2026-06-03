"""
OpenTelemetry setup for Eraya.

Call setup_telemetry() once at Django/ASGI startup (eraya/asgi.py).
Emits spans to Jaeger (or any OTLP collector) when OTEL_EXPORTER_OTLP_ENDPOINT
is set; falls back to a console exporter so dev works with zero infra.

Every ErayaAgent._cascade() call produces a span:
  eraya.<role>.<method>.<tier>
  attributes: agent.id, agent.domain, tier, fallback (bool)
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Generator

logger = logging.getLogger("eraya.telemetry")

# ─── Bootstrap ────────────────────────────────────────────────────────────────

def setup_telemetry(service_name: str = "eraya-swarm") -> None:
    """Initialize the global TracerProvider. Safe to call multiple times."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource({SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("OTel → OTLP at %s", otlp_endpoint)
            except Exception as exc:
                logger.warning("OTLP unavailable (%s), falling back to console", exc)
                provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        else:
            # Console exporter: spans print to stdout — visible in daphne logs
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)

        # Auto-instrument Django HTTP requests → span per view
        try:
            from opentelemetry.instrumentation.django import DjangoInstrumentor
            DjangoInstrumentor().instrument()
            logger.info("OTel Django auto-instrumentation active")
        except Exception:
            pass

        logger.info("OpenTelemetry initialized (service=%s)", service_name)

    except ImportError:
        logger.warning("opentelemetry-sdk not installed — tracing disabled")


# ─── Span helper ──────────────────────────────────────────────────────────────

@contextmanager
def agent_span(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """
    Context manager that creates an OTel span if tracing is configured,
    or is a no-op if it isn't — never raises or swallows user exceptions.

    Usage:
        with agent_span("eraya.perceiver.perceive.tier2", {"agent.id": self.agent_id}):
            result = fn(input_data)
    """
    # Only the OTel *setup* is guarded; user-code exceptions propagate normally.
    try:
        from opentelemetry import trace
        span_ctx = trace.get_tracer("eraya", "0.1.0").start_as_current_span(name)
    except Exception:
        yield None
        return

    with span_ctx as span:
        if span.is_recording() and attributes:
            for k, v in attributes.items():
                span.set_attribute(k, str(v))
        yield span
