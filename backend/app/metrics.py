"""Prometheus metrics (phase 7).

Module-level collectors on the default registry: both the API process and
the standalone worker import the same objects, so each process exports its
own counters/gauges on its own /metrics endpoint (pod-scoped in k8s).
"""

from prometheus_client import Counter, Gauge, Histogram

# ── API ──────────────────────────────────────────────
HTTP_REQUESTS = Counter(
    "http_requests",
    "HTTP requests handled by the API.",
    ["method", "path", "status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "API request latency.",
    ["method", "path"],
)

# ── Worker ───────────────────────────────────────────
WORKER_RUNNING = Gauge(
    "worker_running",
    "1 when the worker loop is running in this process (0 = stopped).",
)
WORKER_CYCLES = Counter(
    "worker_cycles",
    "Successful worker generation cycles.",
)
WORKER_CYCLE_ERRORS = Counter(
    "worker_cycle_errors",
    "Worker cycles that failed (loop survives and retries).",
)
WORKER_LAST_SUCCESS_TIMESTAMP = Gauge(
    "worker_last_success_timestamp_seconds",
    "Unix time of the last successful worker cycle (0 = never succeeded).",
)
SIGNALS_GENERATED = Counter(
    "signals_generated",
    "Signals produced by the worker.",
    ["symbol", "action"],
)
COMMENTARY_SOURCE = Counter(
    "commentary_source",
    "Commentary generations by source (llm:* model or rule-engine fallback).",
    ["source"],
)
