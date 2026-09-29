"""Phase 7: Prometheus metrics — /metrics endpoint + worker counters."""

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.metrics import (
    SIGNALS_GENERATED,
    WORKER_CYCLE_ERRORS,
    WORKER_CYCLES,
    WORKER_LAST_SUCCESS_TIMESTAMP,
)
from app.worker import SignalWorker


def _counter_value(text: str, metric: str) -> float:
    """Sum all ``<metric>{labels} value`` lines in a scrape."""
    vals = [float(m) for m in re.findall(rf"^{metric}\{{.*\}} ([0-9.e+-]+)$", text, re.M)]
    return sum(vals)


def build_worker(interval: int = 3600):
    """Worker wired with the mock provider and a fake commentator."""
    from datetime import UTC, datetime

    from app.ai.commentary import Commentary
    from app.config import Settings
    from app.events import InMemoryEventBus
    from app.providers.mock import MockDataProvider
    from app.services import SignalService
    from app.store import InMemorySignalStore

    class FakeCommentator:
        async def generate(self, signal):
            return Commentary(
                text=f"fake commentary for {signal.symbol}",
                risk_note="fake risk",
                source="rule-engine",
                generated_at=datetime.now(UTC),
            )

    settings = Settings(data_provider="mock", cache_ttl_seconds=0)
    return SignalWorker(
        service=SignalService(provider=MockDataProvider(), settings=settings),
        settings=settings,
        store=InMemorySignalStore(),
        bus=InMemoryEventBus(),
        commentator=FakeCommentator(),
        interval_seconds=interval,
    )


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_text(self):
        client = TestClient(app)
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert "python_info" in resp.text  # default runtime metric present

    def test_http_requests_counter_increments(self):
        client = TestClient(app)
        before = _counter_value(client.get("/metrics").text, "http_requests_total")
        client.get("/health")
        text = client.get("/metrics").text
        assert _counter_value(text, "http_requests_total") == before + 1
        assert 'path="/health"' in text
        assert 'method="GET"' in text

    def test_metrics_scrapes_not_self_counted(self):
        client = TestClient(app)
        text = client.get("/metrics").text
        assert 'path="/metrics"' not in text

    def test_dynamic_paths_use_route_templates(self):
        client = TestClient(app)
        client.get("/api/v1/signals/BTCUSDT")
        text = client.get("/metrics").text
        assert 'path="/api/v1/signals/{symbol}"' in text
        assert "BTCUSDT" not in text  # no raw symbol/path cardinality anywhere


class TestWorkerMetrics:
    async def test_successful_cycle_updates_counters(self):
        worker = build_worker()
        cycles_before = WORKER_CYCLES._value.get()
        sigs_before = sum(c._value.get() for c in SIGNALS_GENERATED._metrics.values())

        signals = await worker.run_cycle()

        assert len(signals) == 3
        assert WORKER_CYCLES._value.get() == cycles_before + 1
        assert sum(c._value.get() for c in SIGNALS_GENERATED._metrics.values()) == sigs_before + 3
        assert WORKER_LAST_SUCCESS_TIMESTAMP._value.get() > 0

    async def test_failed_cycle_increments_error_counter(self):
        worker = build_worker()

        async def boom():
            raise RuntimeError("upstream down")

        worker._service.get_all_signals = boom
        errors_before = WORKER_CYCLE_ERRORS._value.get()

        with pytest.raises(RuntimeError):
            await worker.run_cycle()

        # Counter incremented; the loop (not run_cycle) records last_error.
        assert WORKER_CYCLE_ERRORS._value.get() == errors_before + 1
        assert worker.cycles == 0

    def test_worker_metrics_scrapable(self):
        client = TestClient(app)
        text = client.get("/metrics").text
        assert "worker_cycles_total" in text
        assert "signals_generated_total" in text
        assert "worker_running" in text
        assert "commentary_source_total" in text
