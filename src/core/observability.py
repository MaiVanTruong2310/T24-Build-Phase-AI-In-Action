"""Metrics and tracing setup for the FastAPI service.

Metrics are exposed for Prometheus. OpenTelemetry tracing is opt-in so local
development and the test suite do not require a telemetry backend.
"""

from __future__ import annotations

import os
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


def _enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_tracing(app: Any) -> None:
    """Instrument FastAPI and export spans to the configured OTLP endpoint."""
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.warning("OpenTelemetry dependencies are not installed; tracing is disabled")
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    insecure = _enabled("OTEL_EXPORTER_OTLP_INSECURE", endpoint.startswith("http://"))
    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "ai20k-backend"),
            "deployment.environment.name": os.getenv("OTEL_ENVIRONMENT", os.getenv("APP_ENV", "development")),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=insecure)))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
    logger.info("OpenTelemetry tracing enabled; exporting to %s", endpoint)


def setup_observability(app: Any) -> None:
    """Expose Prometheus metrics and optionally enable OpenTelemetry tracing."""
    if _enabled("METRICS_ENABLED", True):
        try:
            from prometheus_fastapi_instrumentator import Instrumentator
        except ImportError:
            logger.warning("prometheus-fastapi-instrumentator is not installed; metrics are disabled")
        else:
            Instrumentator().instrument(app).expose(
                app,
                endpoint="/metrics",
                include_in_schema=False,
            )

    if _enabled("OTEL_ENABLED"):
        _configure_tracing(app)
